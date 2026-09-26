import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

root_dir = Path(__file__).resolve().parent
jevbench_dir = root_dir / 'bench' / 'jevbench'
endpoint_url = 'http://localhost:3000'
model_name = 'llama-jev'
gpu_hourly_usd = 249 / 730  # Ryzen AI Max+ 395 rental reference: https://gpurack.net/pricing
endpoint_kind = 'gpu'

def main():
  if not jevbench_dir.is_dir():
    subprocess.run(['git', 'clone', 'https://github.com/fstandhartinger/jevbench', str(jevbench_dir)], check=True)

  task_files = sorted((jevbench_dir / 'datasets' / 'public').glob('*.jsonl'),
                      key=lambda path: (['easy', 'original', 'hard'].index(path.stem) if path.stem in ['easy', 'original', 'hard'] else 3,
                                        path.name))
  if not task_files:
    raise SystemExit('JevBench has no public task files')
  task_paths = ','.join(str(path.relative_to(jevbench_dir)) for path in task_files)

  output_dir = root_dir / 'bench' / datetime.now().strftime('run-%Y-%m-%d-%H-%M-%S-%f')
  output_dir.mkdir(parents=True)
  results_path = output_dir / 'results.jsonl'
  ledger_path = output_dir / 'ledger.jsonl'

  run_result = subprocess.run([
    sys.executable, '-m', 'jevbench.cli', 'run',
    '--tasks', task_paths,
    '--adapter', 'typesafe',
    '--endpoint', endpoint_url,
    '--model', model_name,
    '--key-env', '',
    '--cost-basis', 'local_gpu_hosted_rental_estimate',
    '--reserve-usd', '0',
    '--results', str(results_path),
    '--raw-dir', str(output_dir / 'raw'),
    '--ledger', str(ledger_path),
    '--manifest', str(output_dir / 'manifest.json'),
  ], cwd=jevbench_dir)

  if not results_path.exists():
    raise SystemExit(run_result.returncode or 'Benchmark produced no results')

  summary_result = subprocess.run([
    sys.executable, '-m', 'jevbench.cli', 'summarize',
    '--tasks', task_paths,
    '--results', str(results_path),
    '--ledger', str(ledger_path),
  ], cwd=jevbench_dir, check=True, stdout=subprocess.PIPE, text=True)
  (output_dir / 'summary.json').write_text(summary_result.stdout, encoding='utf-8')

  summary = json.loads(summary_result.stdout)
  if run_result.returncode or not summary['complete']:
    raise SystemExit(run_result.returncode or 'Benchmark run is incomplete')

  sys.path.insert(0, str(jevbench_dir))
  scores = score_results(results_path, task_files)
  (output_dir / 'score.json').write_text(json.dumps({
    'model': model_name,
    'dataset_hash': json.loads((output_dir / 'manifest.json').read_text(encoding='utf-8'))['dataset_hash'],
    'cost_basis': 'active request time times estimated GPU rental rate',
    'gpu_hourly_usd': gpu_hourly_usd,
    'scores': scores,
  }, indent=2) + '\n', encoding='utf-8')
  (output_dir / 'score.md').write_text(format_table(scores) + '\n\nPublic proxy; sealed tasks are unavailable. '
                                       + f'Cost uses ${gpu_hourly_usd:.3f}/hour of active request time.\n', encoding='utf-8')
  print(format_terminal(scores))
  print(f'Results: {output_dir}')

def format_table(data):
  lines = [
    '| Dataset | Accuracy | Intelligence | Calibration | Capability | Speed | Cost | $/1k est. | Score proxy |',
    '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |',
  ]
  for tier, entry in data.items():
    lines.append('| ' + ' | '.join(score_cells(tier, entry)) + ' |')
  return '\n'.join(lines)

def format_terminal(data):
  header = ['Dataset', 'Accuracy', 'Intelligence', 'Calibration', 'Capability', 'Speed', 'Cost', '$/1k est.', 'Score proxy']
  rows = [score_cells(tier, entry) for tier, entry in data.items()]
  widths = [max(len(row[i]) for row in [header] + rows) for i in range(len(header))]
  lines = []
  for row in [header, ['-' * width for width in widths]] + rows:
    lines.append('  '.join(cell.rjust(widths[i]) if i else cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip())
  return '\n'.join(lines)

def score_cells(tier, entry):
  axes = ['accuracy', 'intelligence', 'calibration', 'capability', 'speed', 'cost']
  return [tier] + [f'{entry[key]:.1f}' if entry[key] is not None else 'null' for key in axes] + [
    f'{entry["cost_per_1000_usd"]:.4f}' if entry['cost_per_1000_usd'] is not None else 'null',
    f'{entry["score"]:.1f}' if entry['score'] is not None else 'null',
  ]

def score_results(results_path, task_files):
  from jevbench.composite_v13 import chance_corrected_accuracy, intelligence
  from jevbench.summarize import metric
  from jevbench.tasks import load_jsonl

  results = [json.loads(line) for line in results_path.open(encoding='utf-8')]
  tier_tasks = {('standard' if path.stem == 'original' else path.stem): load_jsonl(str(path)) for path in task_files}
  scores = {}
  for tier, tasks in tier_tasks.items():
    task_ids = {task.id for task in tasks}
    records = [result for result in results if result['task_id'] in task_ids]
    metrics = metric(tasks, records)
    intel = chance_corrected_accuracy(metrics['accuracy'], guess_rate(tasks)) if metrics['accuracy'] is not None else None
    scores[tier] = score_axes(metrics, intel, records)

  all_tasks = [task for tasks in tier_tasks.values() for task in tasks]
  global_metrics = metric(all_tasks, results)
  tier_chances = {tier: guess_rate(tasks) for tier, tasks in tier_tasks.items()}
  accuracies = {tier: metric(tasks, results)['accuracy'] for tier, tasks in tier_tasks.items()}
  global_intel = intelligence(accuracies, tier_chances)
  hard_metrics = metric(tier_tasks['hard'], results) if 'hard' in tier_tasks else global_metrics
  scores['public'] = score_axes(global_metrics, global_intel, results, hard_metrics)
  return scores

def guess_rate(tasks):
  return sum(1 / len(task.labels) for task in tasks) / len(tasks)

def score_axes(metrics, intel, records, calibration_metrics=None):
  from jevbench.composite_v13 import calibration, cost, speed
  from jevbench.composite_v14 import harmonic

  calibration_metrics = calibration_metrics or metrics
  cal = calibration(calibration_metrics['ece']['ece']) if calibration_metrics['ece'] else 0.0
  spd = speed(metrics['latency']['p50_s'], metrics['latency']['p95_s'], endpoint_kind)
  latencies = [record.get('latency_s') for record in records]
  usd_per_1000 = 1000 * gpu_hourly_usd * sum(latencies) / (3600 * len(latencies)) if latencies and all(
    latency is not None for latency in latencies) else None
  cst = cost(usd_per_1000) if usd_per_1000 else None
  axes = {'intelligence': intel, 'calibration': cal, 'speed': spd, 'cost': cst}
  return {**axes, 'accuracy': 100 * metrics['accuracy'] if metrics['accuracy'] is not None else None,
          'capability': (intel + cal) / 2 if intel is not None else None,
          'cost_per_1000_usd': usd_per_1000, 'score': harmonic(axes)}

main()
