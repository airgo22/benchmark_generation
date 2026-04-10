
from pathlib import Path 

from wfcommons import BlastRecipe
from wfcommons.wfbench import WorkflowBenchmark , DaskTranslator
from wfcommons import WorkflowGenerator
from format.my_recipe import MyRecipe

# muban : blast -43\ bwa -104\ cycles -67\ epigenomics -41\ genome -52 
        # montage -58\ rnaseq -o63\ seismology -101\ soykb -96\ srasearch -22-104
recipe = MyRecipe.from_num_tasks(
    muban = 'srasearch' ,
    num_tasks = 30 , 
    runtime_factor = 0.5 , 
    input_file_size_factor = 0.05 ,
    output_file_size_factor = 0.08 ,
    num_layers = 5 ,
    sigma = 2.0 ,
    edge_prob = 0.4
    )

generator = WorkflowGenerator(recipe)

count = 10 
for i in range(count) : 
    workflow = generator.build_workflow()
    benchmark = WorkflowBenchmark(recipe=MyRecipe, num_tasks=30)
    # workflow.write_json(Path(f'./tmp/seismology-workflow{i}.json'))
    path = benchmark.create_benchmark_from_synthetic_workflow(Path("./tmp/"), workflow, cpu_work=100, percent_cpu=0.6)

    # translator = DaskTranslator(benchmark.workflow)
    # translator.translate(output_folder=Path("./dask-wf/"))