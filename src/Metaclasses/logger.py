import pandas as pd


class logger(type):
    def __new__(mcs, *args, **kwargs):
        o_log = args[2].get('log', lambda *a, **k: None)
        o_init = args[2].get('__init__', lambda *a, **k: None)

        def log(self, district, lane_name, **info):
            #print("Logging for ", district, " in ", lane_name, ": ", info)
            o_dic = self.logs.get(lane_name, {})
            o_dic[district] = pd.Series(info)
            self.logs[lane_name] = o_dic

        def get_log(self, lane):
            infos = list(self.logs.get(lane,{}).values())
            return pd.DataFrame(infos)

        def __init__(self, *a, **k):
            self.logs = {}
            return o_init(self, *a, **k)

        args[2]['log'] = log
        args[2]['get_log'] = get_log
        args[2]['__init__'] = __init__
        return super().__new__(mcs, *args, **kwargs)

    @classmethod
    def parse_conf(mcs, conf):
        return conf
