import os, sys
import copy
from importlib import import_module
import traceback
from shutil import which

from exlauncher.utils import to_duration, convert_to_command_line

class Launcher(object):
    def __init__(self, exp_name, exp_file, log_dir, n_seeds=1,
                 cpus_per_task=4, memory=20,
                 days=0, hours=48, minutes=0, seconds=0,
                 conda_env=None, gres='gpu:1', partition='short',
                 shell='zsh', account='engs-a2i', reservation=None,):

        self._exp_name = exp_name
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
        
        self._exp_dir_local = os.path.join(log_dir, self._exp_name)
        self._exp_dir_slurm = self._exp_dir_local
        self._exp_dir_slurm_files = os.path.join(self._exp_dir_slurm, 'slurm_files')
        self._exp_dir_slurm_logs = os.path.join(self._exp_dir_slurm, 'slurm_logs')
                
        if not os.path.exists(self._exp_dir_slurm):
            os.makedirs(self._exp_dir_slurm)
        
        self._experiments = []

    def run(self, local, test=False):
        if local:
            self._run_local(test)
        else:
            self._run_slurm(test)

        self._experiments = []    
            
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
            
        

    def _run_slurm(self, test):
        if not os.path.exists(self._exp_dir_slurm_files):
            os.makedirs(self._exp_dir_slurm_files)
        if not os.path.exists(self._exp_dir_slurm_logs):
            os.makedirs(self._exp_dir_slurm_logs)
            
        slurm_files = []
        for i, exp in enumerate(self._experiments):
            command_line = convert_to_command_line(exp)
            
            slurm_files.append(
                self.save_slurm(command_line, str(i))
            )
            
        for slurm_file in slurm_files:
            command = f'sbatch {slurm_file}'
            if test:
                with open(slurm_file, 'r') as f:
                    print(f.read())
                print(command)
            else:
                os.system(command)
                
    def save_slurm(self, command_line, idx: str = None):
        code = self.generate_slurm(command_line)
        
        label = f'_{idx}' if idx is not None else ""
        #TODO: modify script name
        script_name = f'slurm_{self._exp_name}{label}.sh'
        full_path = os.path.join(self._exp_dir_slurm_files, script_name)
        
        with open(full_path, 'w') as f:
            f.write(code)
        return full_path
        
        
    def generate_slurm(self, command_line=None):
        account = ''
        partition = ''
        gres = ''
        reservation = ''
        
        if self._account:
            account = f'#SBATCH --account={self._account}\n'
            
        if self._partition:
            partition = f'#SBATCH --partition={self._partition}\n'
            
        if self._gres:
            gres = f'#SBATCH --gres={self._gres}\n'
            
        if self._reservation:
            reservation = f'#SBATCH --reservation={self._reservation}'
            
        shell = f'#!{which(self._shell)}'
        
        conda_code = ''
        if self._conda_env:
            conda_code = f'conda activate {self._conda_env}\n\n'
        
        python_code = f'python {self.exp_file_path} \\'
        
        
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
#SBATCH --cpus_per_task={self._cpus_per_task}

## output files
#SBATCH --output={self._exp_dir_slurm_logs}/%A_%a.out
#SBATCH --error={self._exp_dir_slurm_logs}/%A_%a.err

# shell command
{self._shell}

###############################################################################
# Your PROGRAM call starts here
echo "Starting Job $SLURM_JOB_ID, Index $SLURM_ARRAY_TASK_ID"

## shell script
{self._shell}

# conda
{conda_code}
"""
        
        code += f"""\
# Program specific arguments

echo "Running scripts in parallel..."
echo "########################################################################"
            
"""
        code += f"""\
{python_code}
\t\t--seed $SLURM_ARRAY_TASK_ID \\
\t\t{command_line}
"""
        return code
                
            
        
            
        

    def add_experiment(self, **kwargs):
        self._experiments.append(copy.deepcopy(kwargs))

    @property
    def exp_file_path(self):
        module = import_module(self._exp_file)
        return module.__file__
