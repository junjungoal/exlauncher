import os, sys
import subprocess

def to_duration(days, hours, minutes, seconds):
    h = "0" + str(hours) if hours < 10 else str(hours)
    m = "0" + str(minutes) if minutes < 10 else str(minutes)
    s = "0" + str(seconds) if seconds < 10 else str(seconds)

    return str(days) + '-' + h + ":" + m + ":" + s

def convert_to_command_line(exp):
    command_line = ''
    for key, value in exp.items():
        new_command = '--' + key + ' '

        if isinstance(value, list):
            new_command += ' '.join(map(str, value)) + ' '
        else:
            new_command += str(value) + ' '

        command_line += new_command

    # remove last space
    command_line = command_line[:-1]

    return command_line

def which(name):
    try:
        # Run 'which zsh' command
        result = subprocess.run(['which', name], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Extract the path from the output
        path = result.stdout.strip()
        return path
    except subprocess.CalledProcessError as e:
        # Handle any errors that occur during subprocess execution
        print("An error occurred: ", e)
        return None
