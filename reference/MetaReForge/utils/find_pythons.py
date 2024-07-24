import subprocess
import re

def find_python_versions_windows():
    # Find all python executables
    try:
        output = subprocess.check_output("where python", shell=True, text=True)
    except subprocess.CalledProcessError:
        return []

    # Split the output by lines and filter out empty lines
    paths = [line.strip() for line in output.strip().split('\n') if line]

    # Use a regex pattern to match the version number when calling python --version
    versions = []
    version_pattern = re.compile(r'Python (\d+\.\d+\.\d+)')

    # Extract the versions
    for path in paths:
        command = f'"{path}" --version'
        try:
            version_output = subprocess.check_output(command, shell=True, text=True, stderr=subprocess.STDOUT)
            match = version_pattern.search(version_output)
            if match:
                version = match.group(1)
                versions.append(version)
        except subprocess.CalledProcessError as ex:
            print(f"Can't run command '{command}': {str(ex)}")
        except Exception as ex:
            print(f"Can't run command '{command}': {str(ex)}")
    return versions


if __name__ == "__main__":
    # Test the function
    print(find_python_versions_windows())
