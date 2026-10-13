#!/usr/bin/env python3
"""Confere invariantes operacionais; execução da GPU é um teste separado."""
from pathlib import Path
import yaml

root = Path(__file__).resolve().parents[1]
docs = [item for item in yaml.safe_load_all((root / 'k8s/resources.yaml').read_text()) if item]
by_kind = {doc['kind']: doc for doc in docs}
assert {'Namespace', 'PersistentVolumeClaim', 'Service', 'Deployment'} <= by_kind.keys()
deployment = by_kind['Deployment']
container = deployment['spec']['template']['spec']['containers'][0]
assert container['image'] != 'vllm/vllm-openai:latest'
assert container['resources']['limits']['nvidia.com/gpu'] == '1'
assert {'startupProbe', 'readinessProbe', 'livenessProbe'} <= container.keys()
assert deployment['spec']['strategy']['type'] == 'Recreate'
assert by_kind['Service']['spec']['type'] == 'ClusterIP'
assert by_kind['PersistentVolumeClaim']['spec']['resources']['requests']['storage']
assert any(a == '--revision' for a in container['args'])
print('Manifestos e requisitos básicos de GPU validados')
