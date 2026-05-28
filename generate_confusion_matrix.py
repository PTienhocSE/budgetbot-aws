import csv
from collections import defaultdict
import sys
import os

# Ensure src module can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.adapters.ai import HybridAI
from src.config import config

def calculate_metrics():
    ai = HybridAI(region=config.aws_region, model_id=config.ai_model_id)
    
    y_true = []
    y_pred = []
    
    print("Evaluating AI categorization on 30+ samples...")
    with open('eval_sample.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            desc = row['description']
            amount = float(row['amount'])
            date = row['date']
            true_cat = row['true_category']
            
            # Predict
            result = ai.categorize(desc, amount, date)
            pred_cat = result['category']
            
            y_true.append(true_cat)
            y_pred.append(pred_cat)
            
            # Print mismatches
            if pred_cat != true_cat:
                print(f"[Mismatch] {desc}: True={true_cat} | Pred={pred_cat}")
                
    # Calculate precision/recall
    categories = sorted(list(set(y_true + y_pred)))
    
    print("\n--- CONFUSION MATRIX ---")
    print(f"{'':>20} " + " ".join([f"{c[:4]:>4}" for c in categories]))
    
    matrix = defaultdict(lambda: defaultdict(int))
    for t, p in zip(y_true, y_pred):
        matrix[t][p] += 1
        
    for t in categories:
        row_str = f"{t:>20} "
        for p in categories:
            row_str += f"{matrix[t][p]:>4} "
        print(row_str)
        
    print("\n--- PRECISION & RECALL ---")
    for cat in categories:
        tp = matrix[cat][cat]
        fp = sum(matrix[t][cat] for t in categories if t != cat)
        fn = sum(matrix[cat][p] for p in categories if p != cat)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        
        print(f"{cat:<20}: Precision={precision:.2f} | Recall={recall:.2f}")

if __name__ == "__main__":
    calculate_metrics()
