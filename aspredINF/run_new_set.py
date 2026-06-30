import argparse
import os
import torch
import pandas as pd
from peft import PeftModel, PeftConfig
from transformers import EsmTokenizer, EsmForSequenceClassification

def predict(model, tokenizer, sequences, threshold=0.5):
    tokens = tokenizer(sequences, padding=True, truncation=True, max_length=512, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**tokens)
        logits = outputs.logits
        probs = torch.softmax(logits, dim=1)
        preds = (probs[:, 1] > threshold).int()
    return logits.tolist(), probs[:, 1].tolist(), preds.tolist()

def main(model_dir, csv_path, threshold=0.5, output_dir=None):
    print(f"Input file: {csv_path}")
    print(f"Model checkpoint: {model_dir}")
    print(f"Classification threshold: {threshold}")

    # Load tokenizer and model (LoRA-wrapped)
    config = PeftConfig.from_pretrained(model_dir)
    base_model = EsmForSequenceClassification.from_pretrained(config.base_model_name_or_path)
    model = PeftModel.from_pretrained(base_model, model_dir)
    tokenizer = EsmTokenizer.from_pretrained(config.base_model_name_or_path)
    model.eval()

    # Load input
    df = pd.read_csv(csv_path)
    if "sequence" not in df.columns:
        raise ValueError("CSV file must contain a 'sequence' column.")

    logits, probs, preds = predict(model, tokenizer, df["sequence"].tolist(), threshold)

    df["logits"] = logits
    df["prob_class1"] = probs
    df["predicted_label"] = preds

    # Decide output file
    basename = os.path.basename(csv_path).replace(".csv", f"__thresh{threshold}_predictions.csv")

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, basename)
    else:
        out_path = os.path.join(os.path.dirname(csv_path), basename)

    df.to_csv(out_path, index=False)

    print(f"Predicted label counts: {pd.Series(preds).value_counts().to_dict()}")
    print(f"Saved predictions to: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_path", required=True)
    parser.add_argument("--input_csv", required=True)
    parser.add_argument("--threshold", type=float, default=0.5, help="Threshold for positive class prediction")
    parser.add_argument("--output_dir", type=str, required=False, default=None, help="Optional output directory")
    args = parser.parse_args()
    main(args.model_path, args.input_csv, threshold=args.threshold, output_dir=args.output_dir)