import os, sys
import copy
from importlib import import_module
import traceback
from shutil import which
import pathlib

from exlauncher.utils import to_duration, convert_to_command_line

class Launcher(object):
    def __init__(self, exp_file, log_dir='./logs', n_seeds=1,
                 cpus_per_task=4, memory=20,
                 days=0, hours=48, minutes=0, seconds=0, wait=None,
                 conda_env=None, gres='gpu:1', partition='short',
                 shell='zsh', account='engs-a2i', reservation=None,):

        self._exp_file = exp_file
        self._n_seeds = n_seeds
        self._duration = to_duration(days, hours, minutes, seconds)
        self._cpus_per_task = cpus_per_task
        self._conda_env = conda_env
        self._gres = gres
        self._partition = partition
        self._reservation = reservation
        self._account = account
        self._shell = shell
        self._memory = memory
        self._wait = wait

        self._log_dir = log_dir
        if not os.path.exists(self._log_dir):
            os.makedirs(self._log_dir)

        self._experiments = {}

    def run(self, local, test=False):
        if local:
            self._run_local(test)
        else:
            self._run_slurm(test)

        self._experiments = {}

    def _run_local(self, test):
        if not test:
            os.makedirs(self._exp_dir_local, exist_ok=True)

        module = import_module(self._exp_file)
        experiment = module.experiment

        if test:
            self._test_experimental_local()

        else:
            default_param_dict = get_experiment_default_params(experiment)
            for param in self._generate_exp_params(default_param_dict):
                try:
                    experiment(**param)
                except Exception:
                    print("Experiment failed with parameters:")
                    print(params)
                    traceback.print_exc()


    def _test_experiment_local(self):
        for exp in zip(self._experiments):
            for i in range(self._n_seeds):
                params = str(exp).replace('{', '(').replace('}', '').replace(': ', '=').replace('\'', '')
                if params:
                    params += ', '
                print('experiment' + params + 'seed=' + str(i) + ')')


    def _create_log_dirs(self, exp_name, slurm=False):
        exp_dir_local = os.path.join(self._log_dir, exp_name)
        if not os.path.exists(exp_dir_local):
            os.makedirs(exp_dir_local)

        if not slurm:
            return exp_dir_local
        else:
            exp_dir_slurm_files = os.path.join(exp_dir_local, 'slurm_files')
            exp_dir_slurm_logs = os.path.join(exp_dir_local, 'slurm_logs')
            if not os.path.exists(exp_dir_slurm_files):
                os.makedirs(exp_dir_slurm_files)
            if not os.path.exists(exp_dir_slurm_logs):
                os.makedirs(exp_dir_slurm_logs)
            return exp_dir_local, exp_dir_slurm_files, exp_dir_slurm_logs

    def _run_slurm(self, test):

        slurm_files = []
        for i, exp_name in enumerate(self._experiments.keys()):
            exp = self._experiments[exp_name]
            command_line = convert_to_command_line(exp)

            slurm_files.append(
                self.save_slurm(command_line, exp_name, str(i))
            )

        for slurm_file in slurm_files:
            command = f'sbatch {slurm_file}'
            if test:
                with open(slurm_file, 'r') as f:
                    print(f.read())
                print(command)
            else:
                os.system(command)

    def save_slurm(self, command_line, exp_name, idx: str = None):
        exp_dir_local, exp_dir_slurm_files, exp_dir_slurm_logs = self._create_log_dirs(exp_name, slurm=True)
        code = self.generate_slurm(command_line, exp_name, exp_dir_slurm_files, exp_dir_slurm_logs, idx)

        label = f'_{idx}' if idx is not None else ""
        #TODO: modify script name
        script_name = f'slurm_{exp_name}{label}.sh'
        full_path = os.path.join(exp_dir_slurm_files, script_name)

        with open(full_path, 'w') as f:
            f.write(code)
        return full_path


    def generate_slurm(self, command_line, exp_name, exp_dir_slurm_files, exp_dir_slurm_logs, idx: str = None):
        account = ''
        partition = ''
        gres = ''
        reservation = ''
        wait = 0

        if self._account:
            account = f'#SBATCH --account={self._account}\n'

        if self._partition:
            partition = f'#SBATCH --partition={self._partition}\n'

        if self._gres:
            gres = f'#SBATCH --gres={self._gres}\n'

        if self._reservation:
            reservation = f'#SBATCH --reservation={self._reservation}'

        if idx is not None and self._wait is not None:
            wait = int(idx) * self._wait

        shell = f'#!{which(self._shell)}'

        conda_code = ''
        if self._conda_env:
            conda_code = f'conda activate {self._conda_env}\n\n'

        python_code = f'python {self._exp_file} \\'


        experiment_args = '\t\t'
        experiment_args += r'${@: 2}'
        experiment_args += ' \\'

        code = f"""\
{shell}

###############################################################################
# SLURM Configurations

{account}{partition}{gres}{reservation}
#SBATCH --nodes=1
#SBATCH --time={self._duration}
#SBATCH --mem={self._memory}G
#SBATCH --array=0-{self._n_seeds - 1}
#SBATCH --cpus-per-task={self._cpus_per_task}

## output files
#SBATCH --output={exp_dir_slurm_logs}/%x.%j.out
#SBATCH --error={exp_dir_slurm_logs}/%x.%j.err

# shell command
{self._shell}
source ~/.{self._shell}rc

###############################################################################
# Your PROGRAM call starts here
echo "Starting Job $SLURM_JOB_ID, Index $SLURM_ARRAY_TASK_ID"

# conda
{conda_code}
"""

        code += f"""\
# Program specific arguments

echo "Running script"
echo "########################################################################"
sleep {wait}

"""
        code += f"""\
{python_code}
\t\t--seed $SLURM_ARRAY_TASK_ID \\
\t\t{command_line}
"""
        return code

    def add_experiment(self, exp_name, **kwargs):
        self._experiments[exp_name] = copy.deepcopy(kwargs)

