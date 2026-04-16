"""
training/run_all_gpu_training.py

Master script to train all ML models for RahatPay Phase 3.
Runs sequentially:
  1. Generate training data
  2. Train XGBoost on GPU (zone risk prediction)
  3. Train Isolation Forest + LOF (fraud detection)
  4. Train Gradient Boosting (spoof detector)

Run this ONCE to generate all models:
    python training/run_all_gpu_training.py

Expected time: ~3-5 minutes on GTX 1650 GPU
Output: 3 .pkl models in models/ directory
"""

import os
import sys
import subprocess
import time

ROOT = os.path.join(os.path.dirname(__file__), "..")

SCRIPTS = [
    ("generate_training_data_gpu.py", "Generating Training Data"),
    ("train_xgboost_gpu.py", "Training XGBoost Zone Risk Model (GPU)"),
    ("train_fraud_models_gpu.py", "Training Fraud Detection Ensemble"),
    ("train_spoof_detector_gpu.py", "Training GPS Spoof Detector"),
]

def run_script(script_name: str, description: str):
    """Run a single training script."""
    script_path = os.path.join(ROOT, "training", script_name)
    
    print("\n" + "=" * 90)
    print(f"▶️  {description}")
    print("=" * 90)
    print()
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            ["python", script_path],
            cwd=ROOT,
            check=True,
            capture_output=False,
            text=True
        )
        
        elapsed = time.time() - start_time
        print(f"\n✅ {description} — COMPLETE ({elapsed:.1f}s)")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} — FAILED")
        print(f"   Error: {e}")
        return False

def main():
    """Run all training scripts in sequence."""
    
    print("\n" + "█" * 90)
    print("█" + " " * 88 + "█")
    print("█" + "  🚀 RAHATPAY ML TRAINING PIPELINE - GPU ACCELERATED (GTX 1650)  ".center(88) + "█")
    print("█" + " " * 88 + "█")
    print("█" * 90)
    print()
    
    print("📋 TRAINING SCHEDULE:")
    print("-" * 90)
    for i, (script, desc) in enumerate(SCRIPTS, 1):
        print(f"{i}. {desc}")
        print(f"   → {script}")
    print()
    
    print("💡 GPU Mode: CUDA GPU acceleration with GTX 1650")
    print("⏱️  Expected total time: 3-5 minutes")
    print()
    
    input("Press Enter to start training...")
    print()
    
    results = {}
    start_total = time.time()
    
    for script_name, description in SCRIPTS:
        success = run_script(script_name, description)
        results[description] = success
        
        if not success:
            print(f"\n⚠️  Training pipeline halted due to error in {description}")
            print("Please fix the error above and re-run.")
            return
    
    elapsed_total = time.time() - start_total
    
    # === SUMMARY ===
    print("\n" + "█" * 90)
    print("█" + " " * 88 + "█")
    print("█" + "  ✨ TRAINING COMPLETE ✨  ".center(88) + "█")
    print("█" + " " * 88 + "█")
    print("█" * 90)
    print()
    
    print("📊 RESULTS:")
    print("-" * 90)
    for description, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status} — {description}")
    print()
    
    print("💾 GENERATED MODELS:")
    print("-" * 90)
    models_dir = os.path.join(ROOT, "models")
    
    expected_models = [
        ("zone_risk_model.pkl", "XGBoost Zone Risk Predictor"),
        ("zone_fraud_iforest.pkl", "IsolationForest Fraud Detector"),
        ("zone_fraud_lof.pkl", "LOF Fraud Detector"),
        ("spoof_detector.pkl", "GPS Spoof Detector"),
    ]
    
    for model_file, description in expected_models:
        model_path = os.path.join(models_dir, model_file)
        if os.path.exists(model_path):
            size_kb = os.path.getsize(model_path) / 1024
            print(f"✅ {model_file:<30} ({size_kb:>6.1f} KB) — {description}")
        else:
            print(f"❌ {model_file:<30} (MISSING)")
    print()
    
    print("📈 METRICS:")
    print("-" * 90)
    
    metrics_files = [
        os.path.join(models_dir, "xgboost_metrics.txt"),
        os.path.join(models_dir, "fraud_model_metrics.txt"),
        os.path.join(models_dir, "spoof_model_metrics.txt"),
    ]
    
    for metrics_file in metrics_files:
        if os.path.exists(metrics_file):
            print(f"\n📄 {os.path.basename(metrics_file)}:")
            try:
                import json
                with open(metrics_file, 'r') as f:
                    metrics = json.load(f)
                    
                # Print key metrics based on file
                if "xgboost" in metrics_file:
                    print(f"   XGBoost R² Score: {metrics['test_metrics']['r2']:.4f}")
                    print(f"   MAE: {metrics['test_metrics']['mae']:.4f}")
                
                elif "fraud" in metrics_file:
                    print(f"   Ensemble Accuracy: {metrics['ensemble_metrics']['test_accuracy']:.4f}")
                    print(f"   Fraud Detection Recall: {metrics['ensemble_metrics']['recall']:.4f}")
                
                elif "spoof" in metrics_file:
                    print(f"   Spoof Detection Accuracy: {metrics['test_metrics']['accuracy']:.4f}")
                    print(f"   Spoof Detection Recall: {metrics['test_metrics']['recall']:.4f}")
            except Exception as e:
                print(f"   (Could not parse metrics: {e})")
    
    print()
    print(f"⏱️  Total time: {elapsed_total:.1f} seconds ({elapsed_total/60:.1f} minutes)")
    print()
    
    print("=" * 90)
    print("✨ All models trained and ready for inference!")
    print("=" * 90)
    print()
    print("NEXT STEPS:")
    print("  1. Start Module 2 server: uvicorn main:app --reload --port 8002")
    print("  2. API endpoints will load models automatically")
    print("  3. Test via: http://localhost:8002/api/model/info")
    print()

if __name__ == "__main__":
    main()
