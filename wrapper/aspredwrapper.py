"""
How to run:

uv run python aspredwrapper.py

or

uv run python aspredwrapper.py --infpath inference_directory --modelpath model_directory
"""

import argparse
import mysql.connector # had to download mysql for windows computer
import csv
import subprocess
import os
import random
import sys
from datetime import datetime

from dotenv import load_dotenv


def parse_arguments():
    parser = argparse.ArgumentParser(description='Path configuration for aspred')
    parser.add_argument('--infpath', 
                       type=str,
                       default='/Users/joeyw/Documents/UCB/Summer_2026/newerAspredFE/aspredFE/aspredINF',
                       help='Path to the inference directory')
    parser.add_argument('--modelpath', 
                       type=str,
                       default='/Users/joeyw/Documents/UCB/Summer_2026/newerAspredFE/aspredFE/aspredINF',
                       help='Path to the model directory')
    
    args = parser.parse_args()
    
    # Verify if the paths exist
    if not os.path.exists(args.infpath):
        raise ValueError(f"Inference path does not exist: {args.infpath}")
    if not os.path.exists(args.modelpath):
        raise ValueError(f"Model path does not exist: {args.modelpath}")
        
    return args.infpath, args.modelpath

# Use it in your code
INFPATH, MODELPATH = parse_arguments()


curdir = os.getcwd()
predfile = 'forASPRED.csv'
predictedfile = predfile.split('.')[0] + '__thresh0.5_predictions.csv' 

#load_dotenv('.env.prod')
load_dotenv(dotenv_path="../local.env") 


db_config = {
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'host': os.getenv('DB_HOST'),
        'database': os.getenv('DB_NAME'),
        'port': os.getenv('DB_PORT')
}


def generate_aspred_input(config):

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        # Query to get pending sequences
        query = """
        SELECT id, sequence 
        FROM sequence_analyzer_sequencesubmission 
        WHERE status = 'pending'
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        if not results:
            print("No new sequences to run the inference")
            sys.exit(1)
        id_lst = [row[0] for row in results]
        
        with open(predfile, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['sequence','_'])
            for _, sequence in results:
                writer.writerow([sequence, 0])
        
        print(f"Created {predfile} with {len(results)} sequences")
        print(f"ID list contains {len(id_lst)} IDs")
        
        return id_lst
        
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        print("Exiting due to an error")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()



def run_prediction(model_filename, input_csv_name):
    # MODELPATH is the global folder from your CLI arguments:    
    
    absolute_model_folder_path = os.path.join(MODELPATH, model_filename)
    # Becomes: /Users/joeyw/.../aspredINF/foldername

    print(f"Executing inference using weights file: {absolute_model_folder_path}")

    subprocess.run([
        'uv', 'run', 'python', os.path.join(INFPATH, 'run_new_set.py'), 
        '--model_path', absolute_model_folder_path, 
        '--input_csv', os.path.join(curdir, input_csv_name)
    ], cwd=INFPATH)


def run_prediction_test():
    """Create mock predictions file"""
    try:
        with open(predfile, 'r', newline='') as infile:
            reader = csv.reader(infile)
            sequences = list(reader)
        with open(predictedfile, 'w', newline='') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(['sequence', 'label', 'predicted_probs', 'predicted_labels'])
            for sequence, label in sequences:
                prob = random.random()
                pred_label = 1 if prob >= 0.5 else 0
                writer.writerow([sequence, label, prob, pred_label])
        print("Created mock predictions file: forASPRED_predictions.csv")
    except FileNotFoundError:
        print("Error: forASPRED.csv not found")
    except Exception as e:
        print(f"Error creating predictions file: {e}")


def read_output():
    """Read the third column from the predictions CSV file"""
    predictions = []
    try:
        with open(predictedfile, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)
            for row in reader:
                if len(row) >= 3: #4
                    predictions.append(row[3]) 
        return predictions
    except FileNotFoundError:
        print(f"Error: {predictedfile} not found 105")
        return []
    except Exception as e:
        print(f"Error reading predictions file: {e}")
        return []


def update_database(id_lst, predictions, config):
    """Update the database with prediction results"""

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        now = datetime.now()
        for id_val, prediction in zip(id_lst, predictions):
            result = float(prediction)
            query = """
            UPDATE sequence_analyzer_sequencesubmission
            SET result = %s, result_date = %s, status = 'done'
            WHERE id = %s
            """
            cursor.execute(query, (result, now, id_val))
        conn.commit()
        print(f"Updated {len(id_lst)} rows in the database")

    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()


def get_pending_tasks_by_model(config):
    """
    Queries pending sequences and groups them by their specific model filename.
    Returns:
        dict: { 'model_filename.safetensors': [(submission_id, sequence), ...] }
    """
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        # We JOIN the submission table with the prediction model table 
        # to get the model_path (which stores the 2 adapter files)
        query = """
        SELECT 
            sub.id, 
            sub.sequence, 
            m.model_path 
        FROM sequence_analyzer_sequencesubmission sub
        JOIN sequence_analyzer_predictionmodel m ON sub.prediction_model_id = m.name
        WHERE sub.status = 'pending'
        ORDER BY sub.id ASC  -- Keeps them in the chronological order they were submitted
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        if not results:
            print("No new sequences to process.")
            return {}

        # Group tasks by their specific model filename
        tasks_by_model = {}
        for sub_id, sequence, model_filename in results:
            if model_filename not in tasks_by_model:
                tasks_by_model[model_filename] = []
            
            # Appending a tuple keeps the ID and its sequence locked together
            tasks_by_model[model_filename].append((sub_id, sequence))
            
        return tasks_by_model
        
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()


def write_input_csv(batch_data, filename):
    """
    Takes a list of tuples [(id, sequence), ...] and writes just 
    the sequences out to the target input CSV file for the ML script.
    """
    try:
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            # Match the exact header your inference script expects
            writer.writerow(['sequence', '_']) 
            
            for _, sequence in batch_data:
                writer.writerow([sequence, 0])
                
        print(f"Successfully created {filename} with {len(batch_data)} sequences.")
    except Exception as e:
        print(f"Error writing input CSV file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 1. Get grouped tasks. 
    # Example structure: {'model_v1.safetensors': [(14, 'ACD...'), (15, 'MKL...')]}
    tasks_by_model = get_pending_tasks_by_model(db_config)
    
    for model_filename, batch_data in tasks_by_model.items():
        print(f"\n--- Processing batch for model filename: {model_filename} ---")
        
        # 2. Extract IDs for THIS batch in the exact order they will be written
        id_lst = [item[0] for item in batch_data]
        
        # 3. Create the input CSV for this model batch
        write_input_csv(batch_data, filename=predfile)

        # 4. Run prediction passing the specific model filename
        run_prediction(model_filename=model_filename, input_csv_name=predfile)
        #If all your models live inside aspredINF, your Django entries for model_path should be the names of those subfolders that contain adapter_config.json and adpter_model.safetensors

        # 5. Read the generated output predictions
        preds_lst = read_output()
        
        # 6. Safety Check: Ensure the inference script returned the same number of rows
        if len(id_lst) == len(preds_lst):
            update_database(id_lst, preds_lst, db_config)
            
            # Clean up the output file so it doesn't leak into the next loop iteration
            full_output_path = os.path.join(INFPATH, predictedfile)
            if os.path.exists(full_output_path):
                os.remove(full_output_path)
        else:
            print(f"CRITICAL ERROR: Row mismatch for {model_filename}!")
            print(f"Expected {len(id_lst)} results, but got {len(preds_lst)}.")

