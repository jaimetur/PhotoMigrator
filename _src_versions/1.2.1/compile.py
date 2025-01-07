import os
import platform
import subprocess

def detect_and_execute(execution_path):
    # Change to exexcution_path folder
    os.chdir(execution_path)
    
    # Detect the operating system
    current_os = platform.system()
    script_name = ""

    # Determine the script name based on the OS
    if current_os == "Linux":
        script_name = "compile_python_linux.sh"
    elif current_os == "Darwin":
        script_name = "compile_python_macos.sh"
    elif current_os == "Windows":
        script_name = "compile_python_win64.bat"
    else:
        print(f"Unsupported operating system: {current_os}")
        return

    # Construct the script path
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", script_name)

    # Check if the script exists
    if not os.path.isfile(script_path):
        print(f"Script not found: {script_path}")
        return

    # Execute the script
    try:
        if current_os == "Windows":
            subprocess.run([script_path], shell=True, check=True)
        else:  # Linux and macOS
            subprocess.run(["bash", script_path], check=True)
        print(f"Successfully executed: {script_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error while executing the script: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    detect_and_execute("../src")
