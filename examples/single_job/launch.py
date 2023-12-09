from exlauncher import Launcher

TEST = True


launcher = Launcher(
    exp_name='test_launcher',
    exp_file='run',
    reservation='a2i202310',
    log_dir='/home/jyamada/projects/exlauncher'
)

launcher.add_experiment(
    arg1='hi'
)
launcher.run(test=TEST)
