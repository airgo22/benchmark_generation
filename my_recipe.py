import pathlib
from logging import Logger
from typing import Optional, Set
import networkx as nx 
import random 
import numpy as np 
import json
import pandas as pd 

from wfcommons.wfchef.wfchef_abstract_recipe import BaseMethod, WfChefWorkflowRecipe
from wfcommons.wfchef.duplicate import duplicate

RECIPES_DIR = pathlib.Path(
    "/opt/miniconda3/envs/wfcommons/lib/python3.10/site-packages/wfcommons/wfchef/recipes/"
    )

class MyRecipe(WfChefWorkflowRecipe):
    def __init__(self,
        # muban : blast \ bwa \ cycles \ epigenomics \ genome 
        # montage \ rnaseq \ seismology \ soykb \ srasearch 
        muban : str = "seismology" ,
        data_footprint: Optional[int] = 0,
        num_tasks: Optional[int] = 50,   # 3 
        exclude_graphs: Set[str] = set(),
        runtime_factor: Optional[float] = 1.0,
        input_file_size_factor: Optional[float] = 1.0,
        output_file_size_factor: Optional[float] = 1.0,
        logger: Optional[Logger] = None,
        base_method: BaseMethod = BaseMethod.ERROR_TABLE,

        # 增加控制正态分布的参数
        num_layers : int = 7 , 
        sigma : float = 1.5 ,
        edge_prob : float = 0.3 , 
        this_dir: Optional[pathlib.Path] = None,

        **kwargs) -> None:
        
        
        if this_dir is None:
            this_dir = RECIPES_DIR / muban

        super().__init__(
            name="MyDAG", 
            data_footprint=data_footprint, 
            num_tasks=num_tasks, 
            exclude_graphs=exclude_graphs, 
            runtime_factor=runtime_factor, 
            input_file_size_factor=input_file_size_factor,
            output_file_size_factor=output_file_size_factor, 
            logger=logger, 
            this_dir=this_dir, 
            base_method=base_method,
            **kwargs
        )

        self.muban = muban 
        self.num_layers = num_layers
        self.sigma = sigma 
        self.edge_prob = edge_prob 

    @classmethod 
    def from_num_tasks(cls,
                num_tasks: int,
                exclude_graphs: Set[str] = set(),
                muban: str = "seismology" ,
                runtime_factor: Optional[float] = 1.0,
                input_file_size_factor: Optional[float] = 1.0,
                output_file_size_factor: Optional[float] = 1.0 , 
                
                num_layers : int = 7 , 
                sigma : float = 1.5 ,
                edge_prob : float = 0.3 , 
                this_dir: Optional[pathlib.Path] = None ,
                ) -> 'WfChefWorkflowRecipe':
        return cls(num_tasks=num_tasks,
                exclude_graphs=exclude_graphs,
                runtime_factor=runtime_factor,
                input_file_size_factor=input_file_size_factor,
                output_file_size_factor=output_file_size_factor,

                muban = muban ,
                num_layers = num_layers, 
                sigma = sigma, 
                edge_prob = edge_prob, 
                this_dir = this_dir 
            )
        

    def generate_nx_graph(self) -> nx.DiGraph:
        """
        重写generate_nx_graph
        生成的DAG在任务数量/负载上呈现正态分布 
        """
        summary_path = self.this_dir.joinpath("microstructures", "summary.json")
        summary = json.loads(summary_path.read_text())

        metric_path = self.this_dir.joinpath("microstructures", "metric", "err.csv")
        df = pd.read_csv(str(metric_path), index_col=0)
        df = df.drop(self.exclude_graphs, axis=0, errors="ignore")
        df = df.drop(self.exclude_graphs, axis=1, errors="ignore")
        for col in df.columns:
            df.loc[col, col] = np.nan


        # 从期望任务数周围采样呈现正态分布的任务数
        mean_tasks = float(self.num_tasks) 
        sigma_tasks = max(self.sigma , 1.0)  if self.sigma else max(1.0 , 0.1 * mean_tasks) 
        sampled_tasks = int(np.random.normal(loc = mean_tasks , scale = sigma_tasks))

        # 将采样的任务数规范在模版的任务范围之内 
        base_orders = [v["order"] for v in summary["base_graphs"].values()]
        min_order = min(base_orders)
        max_order = max(base_orders) 
        actual_num_tasks = max(min_order, min(sampled_tasks, max_order))

        
        # self.task_num -> actual_num_tasks 
        reference_orders = [summary["base_graphs"][col]["order"] for col in df.columns]
        idx = np.argmin([abs(actual_num_tasks - ref_num_tasks) for ref_num_tasks in reference_orders])
        reference = df.columns[idx]

        if self.base_method == BaseMethod.ERROR_TABLE:
            base = df[reference].idxmin()
        elif self.base_method == BaseMethod.SMALLEST:
            base = min(
                [k for k in summary["base_graphs"].keys() if summary["base_graphs"][k] not in self.exclude_graphs],
                key=lambda k: summary["base_graphs"][k]["order"]
            )
        elif self.base_method == BaseMethod.BIGGEST:
            base = max(
                [k for k in summary["base_graphs"].keys() if summary["base_graphs"][k]["order"] <= actual_num_tasks  and
                summary["base_graphs"][k] not in self.exclude_graphs],
                key=lambda k: summary["base_graphs"][k]["order"]
            )
        else:
            base = random.choice(
                [k for k in summary["base_graphs"].keys() if summary["base_graphs"][k]["order"] <= actual_num_tasks  and
                summary["base_graphs"][k] not in self.exclude_graphs]
            )
    
        graph = duplicate(self.this_dir.joinpath("microstructures"), base, actual_num_tasks )
        return graph

