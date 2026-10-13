# vLLM no Kubernetes: servir um modelo com GPU e medir o resultado

Este laboratório organiza o deploy de uma API de inferência OpenAI compatível em Kubernetes. A escolha foi um modelo pequeno, `Qwen/Qwen2.5-0.5B-Instruct`, com revisão fixa, para concentrar o projeto no que costumo investigar em plataforma: agendamento de GPU, tempo de inicialização, cache, health checks, consumo de recursos e latência.

**Estado da validação:** o CI verifica a estrutura dos manifestos, a renderização com Kustomize e o script de medição. Não afirmo que executei inferência nem testes de carga em GPU neste repositório: essa parte exige um cluster com GPU NVIDIA e disponibilidade do modelo. O roteiro abaixo permite reproduzir e registrar os resultados nesse ambiente.

## Pré-requisitos

- Kubernetes com uma GPU NVIDIA disponível no nó, driver compatível com a imagem escolhida e device plugin anunciando `nvidia.com/gpu`.
- StorageClass padrão capaz de provisionar um PVC de 10 GiB; acesso ao Hugging Face para baixar o modelo; memória de GPU suficiente para modelo e KV cache. Ajuste limites após medir no equipamento real.
- `kubectl` com acesso ao namespace que será criado. O Service é `ClusterIP`; não há exposição pública.

## Execução no cluster

```bash
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\\.com/gpu
kubectl apply -k k8s/
kubectl -n llm-lab get pods,pvc,svc
kubectl -n llm-lab rollout status deployment/vllm --timeout=20m
kubectl -n llm-lab port-forward svc/vllm 8000:8000
```

Em outro terminal:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/v1/models
python3 scripts/bench.py --requests 10 --concurrency 2
curl -fsS http://127.0.0.1:8000/metrics | head
```

`bench.py` devolve total, sucessos, erros, RPS e latências p50/p95. O prompt e o limite de saída são fixos para comparar rodadas. Registre GPU, modelo, versão, concorrência e medições antes de comparar números; o script mede tempo total de cada resposta, não TTFT, throughput de tokens ou qualidade do modelo.

## Escolhas operacionais

- `startupProbe` aceita até 15 minutos para pull/download e carga do modelo, sem uma `livenessProbe` matá-lo durante a inicialização. Depois, `/health` cobre readiness e liveness; `/metrics` expõe métricas Prometheus. Aplique alertas conforme a carga real.
- PVC evita baixar tudo a cada reinício. `Recreate` permite atualizar a única réplica com um volume RWO e uma GPU sem exigir duas GPUs simultâneas, mas causa uma janela de indisponibilidade. Para alta disponibilidade, seriam necessários mais capacidade, replicação e estratégia de tráfego.
- O exemplo não cria token de API nem Ingress. Não exponha esse Service diretamente à internet; acrescente autenticação, TLS, limites de requisição, política de rede e gateway apropriado antes de uso compartilhado.
- A imagem `vllm/vllm-openai:v0.11.0` e a revisão do modelo estão fixas para reduzir variação. Para uma política de supply chain mais rígida, fixe também o digest da imagem após validá-lo no registry.

Referências: [vLLM API e endpoints](https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html), [vLLM métricas](https://docs.vllm.ai/en/stable/usage/metrics/), [Kubernetes GPUs](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/). A ideia “vLLM on Kubernetes” veio do [vídeo de Vishakha Sadhwani](https://www.youtube.com/watch?v=79jr3CgBY-Q); o material aqui é um ambiente de homologação, sem informações corporativas.
