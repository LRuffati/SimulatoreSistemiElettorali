import src.GlobalVars
from runpy import run_path
import sys
import pandas as pd
import src
import os
from src.Metaclasses import *
import src.GlobalVars as GlobalVars
import yaml

from src import Commons
from src.Metaclasses import sources_parse
from src.Metaclasses.cleanup import cleanup

commons = Commons


def run_simulation(path):
    """
    Given a path to the input folder it runs the simulation of the election

    Overview of steps:
    1. Create the Hub, this works as a global variable space with some support
        functions tailored to the project
    2. Read the configuration files for the Classes, for each of these, if it's
        a python file execute it and "import" the class, if they're a yaml file
        then evaluate the metaclasses it needs and then pass the configuration
        to these to create the concrete classes
    3. Read the files describing the instances and pass them to the corresponding
        class created in step 2 as keyword arguments.
        NB: during the creation of the instance the unique name provided to each
        instance is associated to the instance in the Hub as well as other
        information provided by metaclasess
    4. Read the data (the votes in the election) and provide it to the specified
        instances through method calls
    5. Run the election through the hub
    """
    src.GlobalVars.Hub = src.GlobalVars.ActHub() # 1
    base_path = path
    classes = next(os.walk(os.path.join(base_path, 'Classes')))
    for i in classes[2]: # 2
        pth = os.path.join(base_path, 'Classes', i)
        name = i.split('.')[0]

        if '.py' in i:
            d = run_path(pth, globals())
            exec(f"{name} = d['{name}']")
        elif '.yaml' in i:
            with open(pth, 'r') as f:
                conf = yaml.safe_load(f)
            metas = [eval(i) for i in conf.pop('metaclasses')]
            for i in metas:
                conf = i.parse_conf(conf) # parse conf is a method of each metaclass

            conf = sources_parse.source_parse(conf)
            metas_f = tuple(metas + [cleanup])
            comb = type(f'comb_{name}', metas_f, {}) # create the combined metaclass

            c = comb(name, (), {}, **conf) # create the class
            exec(f'{name}=c') # insert the class into the namespace of the program

    instances = next(os.walk(os.path.join(base_path, 'Instances')))
    for i in instances[2]: # 3
        print(i)
        cls = eval(i.split('.')[0])
        with open(os.path.join(base_path, 'Instances', i), 'r') as f:
            d = yaml.safe_load(f)
            for k, conf in d.items():
                print(k)
                cls(k, **conf)

    data = next(os.walk(os.path.join(base_path, 'Data')))
    for f in data[1]: # 4
        path = os.path.join(base_path, 'Data', f)
        for csv in next(os.walk(path))[2]:
            name = csv.split('.')[0]
            df = pd.read_csv(os.path.join(path, csv))
            for k, data in df.groupby(df.columns[0]):
                r = GlobalVars.Hub.get_instance(f, k)
                getattr(r, f'give_{name}')(data.iloc[:, 1:])

    return src.GlobalVars.Hub.run_exec() # 5