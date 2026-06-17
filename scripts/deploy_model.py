#!/usr/bin/env python3
"""
Model Deployment Utility for HealSense
Converts trained models to mobile-ready formats and validates deployment
"""

import tensorflow as tf
import numpy as np
import json
import os
import time
from pathlib import Path
import argparse

class ModelDeployer:
    """Handle model conversion and deployment validation"""
    
    def __init__(self, model_path, output_dir='../data/models/tflite'):
        self.model_path = model_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model = None
        
    def load_model(self):
        """Load Keras model"""
        print(f"📦 Loading model from: {self.model_path}")
        self.model = tf.keras.models.load_model(self.model_path)
        print("   ✓ Model loaded successfully\n")
        return self.model
    
    def convert_to_tflite(self, quantization='float16'):
        """
        Convert Keras model to TFLite format
        
        Args:
            quantization: 'none', 'float16', or 'int8'
        """
        print(f"🔄 Converting to TFLite (quantization: {quantization})...")
        
        converter = tf.lite.TFLiteConverter.from_keras_model(self.model)
        
        if quantization == 'float16':
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
            converter.target_spec.supported_types = [tf.float16]
            suffix = '_float16'
        elif quantization == 'int8':
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
            # For int8, you'd need a representative dataset
            # converter.representative_dataset = representative_dataset_gen
            suffix = '_int8'
        else:
            suffix = ''
        
        tflite_model = converter.convert()
        
        # Save model
        output_path = self.output_dir / f'health_model{suffix}.tflite'
        with open(output_path, 'wb') as f:
            f.write(tflite_model)
        
        # Get size
        size_mb = os.path.getsize(output_path) / (1024**2)
        
        print(f"   ✓ Saved: {output_path}")
        print(f"   ✓ Size: {size_mb:.2f} MB\n")
        
        return output_path, size_mb
    
    def benchmark_tflite(self, tflite_path, num_runs=100):
        """Benchmark TFLite model inference speed"""
        print(f"⏱️  Benchmarking inference speed ({num_runs} runs)...")
        
        interpreter = tf.lite.Interpreter(model_path=str(tflite_path))
        interpreter.allocate_tensors()
        
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        
        # Create random test input
        input_shape = input_details[0]['shape']
        test_input = np.random.randn(*input_shape).astype(np.float32)
        
        # Warmup
        for _ in range(10):
            interpreter.set_tensor(input_details[0]['index'], test_input)
            interpreter.invoke()
        
        # Benchmark
        latencies = []
        for _ in range(num_runs):
            start = time.time()
            interpreter.set_tensor(input_details[0]['index'], test_input)
            interpreter.invoke()
            latencies.append((time.time() - start) * 1000)
        
        avg_latency = np.mean(latencies)
        std_latency = np.std(latencies)
        min_latency = np.min(latencies)
        max_latency = np.max(latencies)
        
        print(f"   Average: {avg_latency:.2f} ms")
        print(f"   Std Dev: {std_latency:.2f} ms")
        print(f"   Min:     {min_latency:.2f} ms")
        print(f"   Max:     {max_latency:.2f} ms")
        
        if avg_latency < 50:
            print("   ✓ Excellent for mobile deployment!")
        elif avg_latency < 100:
            print("   ✓ Good for mobile deployment")
        else:
            print("   ⚠️ May be slow on low-end devices")
        
        print()
        return {
            'avg': avg_latency,
            'std': std_latency,
            'min': min_latency,
            'max': max_latency
        }
    
    def validate_accuracy(self, tflite_path, test_data, test_labels):
        """Compare TFLite model accuracy with original"""
        print("🎯 Validating model accuracy...")
        
        # Original model predictions
        orig_preds = self.model.predict(test_data, verbose=0)
        orig_classes = np.argmax(orig_preds, axis=1)
        
        # TFLite predictions
        interpreter = tf.lite.Interpreter(model_path=str(tflite_path))
        interpreter.allocate_tensors()
        
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        
        tflite_preds = []
        for i in range(len(test_data)):
            test_sample = test_data[i:i+1].astype(np.float32)
            interpreter.set_tensor(input_details[0]['index'], test_sample)
            interpreter.invoke()
            output = interpreter.get_tensor(output_details[0]['index'])
            tflite_preds.append(np.argmax(output[0]))
        
        tflite_preds = np.array(tflite_preds)
        
        # Calculate metrics
        orig_acc = np.mean(orig_classes == test_labels)
        tflite_acc = np.mean(tflite_preds == test_labels)
        agreement = np.mean(orig_classes == tflite_preds)
        
        print(f"   Original Model Accuracy: {orig_acc*100:.2f}%")
        print(f"   TFLite Model Accuracy:   {tflite_acc*100:.2f}%")
        print(f"   Prediction Agreement:    {agreement*100:.2f}%")
        
        if abs(orig_acc - tflite_acc) < 0.02:
            print("   ✓ Accuracy maintained!")
        else:
            print("   ⚠️ Accuracy degradation detected")
        
        print()
        return {
            'original_accuracy': float(orig_acc),
            'tflite_accuracy': float(tflite_acc),
            'agreement': float(agreement)
        }
    
    def generate_deployment_config(self, model_info):
        """Generate configuration for mobile deployment"""
        config = {
            'model_version': '1.0.0',
            'deployment_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'model_info': model_info,
            'input_shape': self.model.input_shape[1:],
            'output_classes': self.model.output_shape[-1],
            'preprocessing': {
                'normalization': 'StandardScaler',
                'sequence_length': self.model.input_shape[1],
                'features': ['heart_rate', 'spo2', 'temperature', 'systolic_bp', 'diastolic_bp']
            },
            'thresholds': {
                'confidence_threshold': 0.7,
                'critical_threshold': 0.8
            }
        }
        
        config_path = self.output_dir / 'deployment_config.json'
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"📄 Deployment config saved: {config_path}\n")
        return config_path
    
    def create_flutter_integration_guide(self):
        """Generate Flutter integration code snippet"""
        guide = """
# Flutter Integration Guide for HealSense Model

## 1. Add Dependency
Add to `pubspec.yaml`:
```yaml
dependencies:
  tflite_flutter: ^0.10.0
```

## 2. Copy Model Files
Copy these files to `assets/`:
- health_model_float16.tflite
- scaler.pkl (convert to JSON for Flutter)
- label_encoder.pkl (convert to JSON)

Update `pubspec.yaml`:
```yaml
flutter:
  assets:
    - assets/health_model_float16.tflite
    - assets/scaler_params.json
    - assets/label_mapping.json
```

## 3. Load Model in Flutter
```dart
import 'package:tflite_flutter/tflite_flutter.dart';

class HealthPredictor {
  Interpreter? _interpreter;
  
  Future<void> loadModel() async {
    _interpreter = await Interpreter.fromAsset('health_model_float16.tflite');
    print('Model loaded successfully');
  }
  
  Future<Map<String, dynamic>> predict(List<List<double>> sequence) async {
    if (_interpreter == null) await loadModel();
    
    // Input: [1, 60, 5] (batch, timesteps, features)
    var input = [sequence];
    
    // Output: [1, 3] (batch, classes)
    var output = List.filled(3, 0.0).reshape([1, 3]);
    
    _interpreter!.run(input, output);
    
    // Get prediction
    List<double> probabilities = output[0];
    int predictedClass = probabilities.indexOf(probabilities.reduce((a, b) => a > b ? a : b));
    double confidence = probabilities[predictedClass];
    
    List<String> classes = ['normal', 'warning', 'critical'];
    
    return {
      'status': classes[predictedClass],
      'confidence': confidence,
      'probabilities': {
        'normal': probabilities[0],
        'warning': probabilities[1],
        'critical': probabilities[2],
      }
    };
  }
  
  void dispose() {
    _interpreter?.close();
  }
}
```

## 4. Normalize Input Data
```dart
// Load scaler parameters from assets/scaler_params.json
Map<String, List<double>> scalerParams = {
  'mean': [75.0, 97.5, 36.8, 118.0, 78.0],
  'std': [10.0, 1.2, 0.3, 8.0, 6.0]
};

List<List<double>> normalizeSequence(List<Map<String, double>> vitalReadings) {
  return vitalReadings.map((reading) {
    return [
      (reading['heart_rate']! - scalerParams['mean']![0]) / scalerParams['std']![0],
      (reading['spo2']! - scalerParams['mean']![1]) / scalerParams['std']![1],
      (reading['temperature']! - scalerParams['mean']![2]) / scalerParams['std']![2],
      (reading['systolic_bp']! - scalerParams['mean']![3]) / scalerParams['std']![3],
      (reading['diastolic_bp']! - scalerParams['mean']![4]) / scalerParams['std']![4],
    ];
  }).toList();
}
```

## 5. Usage Example
```dart
void main() async {
  final predictor = HealthPredictor();
  await predictor.loadModel();
  
  // Simulate 60 minutes of vital signs
  List<Map<String, double>> vitalReadings = [
    {'heart_rate': 75, 'spo2': 98, 'temperature': 36.8, 'systolic_bp': 120, 'diastolic_bp': 80},
    // ... 59 more readings
  ];
  
  // Normalize and predict
  var normalizedSeq = normalizeSequence(vitalReadings);
  var result = await predictor.predict(normalizedSeq);
  
  print('Status: ${result['status']}');
  print('Confidence: ${result['confidence']}');
  
  if (result['status'] == 'critical') {
    // Trigger emergency alert
    sendWhatsAppAlert();
  }
}
```

## 6. Testing on Device
- Test on Android: `flutter run`
- Test on iOS: `flutter run -d ios`
- Measure latency: `Stopwatch().start()` before prediction
- Target: < 100ms inference time

## 7. Security Considerations
- Never send raw patient data unencrypted
- Store models in secure storage on device
- Implement certificate pinning for API calls
- Use flutter_secure_storage for sensitive data
"""
        
        guide_path = self.output_dir / 'FLUTTER_INTEGRATION.md'
        with open(guide_path, 'w') as f:
            f.write(guide)
        
        print(f"📖 Flutter integration guide: {guide_path}\n")


def main():
    parser = argparse.ArgumentParser(description='Deploy HealSense model for mobile')
    parser.add_argument('--model', type=str, default='../data/models/checkpoints/lstm_best.h5',
                        help='Path to trained Keras model')
    parser.add_argument('--output', type=str, default='../data/models/tflite',
                        help='Output directory for TFLite models')
    parser.add_argument('--quantization', type=str, default='float16',
                        choices=['none', 'float16', 'int8'],
                        help='Quantization type')
    parser.add_argument('--skip-validation', action='store_true',
                        help='Skip accuracy validation (faster)')
    
    args = parser.parse_args()
    
    print("="*70)
    print("🚀 HEALSENSE MODEL DEPLOYMENT UTILITY")
    print("="*70)
    print()
    
    # Initialize deployer
    deployer = ModelDeployer(args.model, args.output)
    
    # Load model
    deployer.load_model()
    
    # Convert to TFLite
    tflite_path, model_size = deployer.convert_to_tflite(args.quantization)
    
    # Benchmark
    benchmark_results = deployer.benchmark_tflite(tflite_path)
    
    # Validation (if test data available)
    validation_results = None
    if not args.skip_validation:
        try:
            # Load test data (you'd need to save this from training)
            print("⚠️ Validation requires test data from training")
            print("   Run the training notebook first and save test data\n")
        except:
            pass
    
    # Generate deployment artifacts
    model_info = {
        'size_mb': model_size,
        'quantization': args.quantization,
        'latency': benchmark_results
    }
    
    if validation_results:
        model_info['accuracy'] = validation_results
    
    deployer.generate_deployment_config(model_info)
    deployer.create_flutter_integration_guide()
    
    print("="*70)
    print("✅ DEPLOYMENT COMPLETE")
    print("="*70)
    print(f"\n📦 Artifacts saved in: {args.output}/")
    print("\nNext steps:")
    print("  1. Copy TFLite model to Flutter project assets/")
    print("  2. Follow FLUTTER_INTEGRATION.md for implementation")
    print("  3. Test on real device")
    print()


if __name__ == "__main__":
    main()
