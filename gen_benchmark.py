
from pathlib import Path 

from wfcommons import BlastRecipe
from wfcommons.wfbench import WorkflowBenchmark , DaskTranslator
from wfcommons import WorkflowGenerator
from my_recipe import MyRecipe


recipe = MyRecipe.from_num_tasks(
    muban = 'blast' ,
    num_tasks = 50 , 
    runtime_factor = 1.1 , 
    input_file_size_factor = 1.5 ,
    output_file_size_factor = 0.8 ,
    )

generator = WorkflowGenerator(recipe)

count = 1 
for i in range(count) : 
    workflow = generator.build_workflow()
    benchmark = WorkflowBenchmark(recipe=MyRecipe, num_tasks=50)
    # workflow.write_json(Path(f'./tmp/seismology-workflow{i}.json'))
    path = benchmark.create_benchmark_from_synthetic_workflow(Path("./tmp/"), workflow, cpu_work=100, percent_cpu=0.6)

    # translator = DaskTranslator(benchmark.workflow)
    # translator.translate(output_folder=Path("./dask-wf/"))