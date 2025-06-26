#!/usr/bin/env python3
"""
Flutter Server Runner
Run this script to start the Flutter development server with Poetry.
"""

import os
import sys
import subprocess
import shutil
import time
import signal

def check_flutter():
    """Check if Flutter is installed and available."""
    try:
        result = subprocess.run(['flutter', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Flutter is installed")
            return True
        else:
            print("✗ Flutter check failed")
            return False
    except FileNotFoundError:
        print("✗ Flutter is not installed or not in PATH")
        return False

def check_poetry():
    """Check if we're running in Poetry environment."""
    # Check for Poetry environment variables or if running via poetry run
    if (os.environ.get('POETRY_ACTIVE') or 
        os.environ.get('VIRTUAL_ENV') and 'poetry' in os.environ.get('VIRTUAL_ENV', '') or
        'poetry' in sys.argv[0] or
        os.path.exists('poetry.lock')):
        print("✓ Running with Poetry")
        return True
    else:
        print("✗ Not running in Poetry environment")
        print("Please run: poetry run python run.py")
        return False

def reset_flutter_project():
    """Reset Flutter project to simple counter app."""
    print("\n🔄 Resetting Flutter project to counter app...")
    
    project_dir = "project"
    
    try:
        # Stop any running Flutter processes first
        print("  • Stopping any running Flutter processes...")
        try:
            # Find actual Flutter development server processes (not this Python script)
            result = subprocess.run(['pgrep', '-f', 'flutter run'], capture_output=True, text=True)
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                current_pid = os.getpid()
                for pid in pids:
                    if pid and pid.strip() != str(current_pid):
                        try:
                            # Check if it's actually a Flutter process, not our Python script
                            proc_info = subprocess.run(['ps', '-p', pid.strip(), '-o', 'cmd='], 
                                                     capture_output=True, text=True)
                            if proc_info.returncode == 0 and 'flutter run' in proc_info.stdout and 'python' not in proc_info.stdout:
                                os.kill(int(pid), signal.SIGTERM)
                        except:
                            pass
                time.sleep(2)  # Give time for graceful shutdown
        except:
            pass  # Ignore errors if no processes to kill
        
        # Wait a moment for processes to stop
        time.sleep(2)
        
        # Remove existing project directory if it exists
        if os.path.exists(project_dir):
            print(f"  • Removing existing {project_dir} directory...")
            # Try multiple times in case files are still locked
            for attempt in range(3):
                try:
                    shutil.rmtree(project_dir)
                    break
                except OSError as e:
                    if attempt < 2:
                        print(f"    Retry {attempt + 1}/3...")
                        time.sleep(1)
                    else:
                        raise e
        
        # Create new Flutter project
        print("  • Creating fresh Flutter project...")
        result = subprocess.run(
            ['flutter', 'create', project_dir], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            print(f"✗ Failed to create Flutter project: {result.stderr}")
            return False
        
        # Counter app template
        counter_app_code = '''import 'package:flutter/material.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Flutter Counter Demo',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const MyHomePage(title: 'Flutter Counter App'),
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key, required this.title});

  final String title;

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  int _counter = 0;

  void _incrementCounter() {
    setState(() {
      _counter++;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: Text(widget.title),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            const Text(
              'You have pushed the button this many times:',
            ),
            Text(
              '$_counter',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _incrementCounter,
        tooltip: 'Increment',
        child: const Icon(Icons.add),
      ),
    );
  }
}
'''
        
        # Write the counter app code to main.dart
        main_dart_path = os.path.join(project_dir, 'lib', 'main.dart')
        print("  • Writing counter app code to main.dart...")
        with open(main_dart_path, 'w', encoding='utf-8') as f:
            f.write(counter_app_code)
        
        # Get Flutter dependencies to ensure everything is ready
        print("  • Getting Flutter dependencies...")
        get_result = subprocess.run(
            ['flutter', 'pub', 'get'], 
            cwd=project_dir,
            capture_output=True, 
            text=True
        )
        
        if get_result.returncode != 0:
            print(f"    Warning: Flutter pub get failed: {get_result.stderr}")
        
        # Remove test directory to keep it clean
        test_dir = os.path.join(project_dir, 'test')
        if os.path.exists(test_dir):
            print("  • Removing test directory...")
            shutil.rmtree(test_dir)
        
        print("✓ Flutter counter app created successfully")
        return True
        
    except Exception as e:
        print(f"✗ Error resetting Flutter project: {e}")
        return False

def main():
    print("Flutter Development Server")
    print("=" * 30)
    
    # Check requirements
    if not check_flutter():
        print("\nPlease install Flutter first:")
        print("https://docs.flutter.dev/get-started/install")
        sys.exit(1)
    
    if not check_poetry():
        print("\nTo run with Poetry:")
        print("poetry run python run.py")
        sys.exit(1)
    
    # Reset Flutter project to counter app
    if not reset_flutter_project():
        print("\n✗ Failed to reset Flutter project")
        sys.exit(1)
    
    print("\n🚀 Starting Flutter development server...")
    print("Access the web interface at: http://localhost:5000")
    print("Flutter app: Simple counter app ready for development")
    print("Press Ctrl+C to stop")
    
    # Import and run the new modular application
    from src.main import main as run_server
    try:
        run_server()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down Flutter development server...")
        sys.exit(0)

if __name__ == '__main__':
    main()