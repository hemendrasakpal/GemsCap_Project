# run_all.py
import os
import subprocess
import sys
import time


def run_command(command, cwd=None):
    """Run a command as a subprocess."""
    return subprocess.Popen(command, cwd=cwd, shell=True)


if __name__ == "__main__":
    print("🚀 Starting GemsCap Quant Platform...")

    # Paths
    backend_dir = os.getcwd()
    streamlit_dir = os.path.join(os.getcwd(), "streamlit_app")
    collector_dir = os.path.join(os.getcwd(), "collector")

    # Start Django backend
    print("📡 Starting Django backend on http://127.0.0.1:8000 ...")
    backend = run_command("python manage.py runserver 8000", cwd=backend_dir)
    time.sleep(3)

    # Start collector (optional)
    print("🔁 Starting collector...")
    collector = run_command("python collector.py", cwd=collector_dir)
    time.sleep(2)

    # Start Streamlit frontend
    print("💻 Starting Streamlit app on http://localhost:8501 ...")
    streamlit = run_command("streamlit run app.py --server.port 8501", cwd=streamlit_dir)

    print("\n✅ All services started successfully!")
    print("Django → http://127.0.0.1:8000/api/")
    print("Streamlit → http://localhost:8501")
    print("\nPress CTRL+C to stop everything.\n")

    try:
        backend.wait()
        collector.wait()
        streamlit.wait()
    except KeyboardInterrupt:
        print("🛑 Shutting down all processes...")
        backend.terminate()
        collector.terminate()
        streamlit.terminate()
        sys.exit(0)
