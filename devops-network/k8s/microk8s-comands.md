# Microk8s Kubectl

+++
+++
+++

## Команды самого microk8s (аддоны, статус, конфиг)

Эти команды управляют самим кластером, а не ресурсами внутри него.

```bash
# Статус кластера и список включенных аддонов
microk8s status --wait-ready

# Включить аддон (например, DNS, ingress, dashboard, metallb)
microk8s enable dns ingress dashboard metallb

# Отключить аддон
microk8s disable ingress

# Получить kubeconfig, чтобы использовать свой kubectl (если alias не настроен)
microk8s config > ~/.kube/config

# Посмотреть список доступных аддонов
microk8s list-addons
Для тебя с alias: чаще всего достаточно microk8s status и microk8s enable, остальное делается через kubectl.
```

+++
+++
+++

## Базовые команды kubectl (просмотр ресурсов)

Так как у тебя alias, можно писать просто kubectl вместо microk8s kubectl.

```bash
# Посмотреть все поды во всех неймспейсах
kubectl get pods -A

# Поды в текущем неймспейсе (по умолчанию default)
kubectl get pods

# Деплойменты, сервисы, ингрессы, конфигмапы, секреты — по отдельности
kubectl get deployments
kubectl get services
kubectl get ingresses
kubectl get configmaps
kubectl get secrets

# Всё сразу в одном неймспейсе
kubectl get all

# Детали конкретного ресурса (например, пода)
kubectl describe pod <pod-name>

# Логи пода (очень часто нужно при отладке)
kubectl logs <pod-name>
# Если в поде несколько контейнеров:
kubectl logs -c <container-name> <pod-name>

# Следить за событиями в реальном времени (полезно при создании/удалении)
kubectl get events --watch
```

+++
+++
+++

## Управление ресурсами (создание, применение, удаление)

```bash
# Применить манифест (Deployment, Service, ConfigMap и т.д.)
kubectl apply -f manifest.yaml

# Применить все YAML-файлы из папки
kubectl apply -k ./k8s-manifests

# Удалить ресурс по файлу
kubectl delete -f manifest.yaml

# Удалить по имени и типу
kubectl delete deployment hello-app
kubectl delete service hello-service

# Масштабировать деплоймент (например, до 5 реплик)
kubectl scale deployment hello-app --replicas=5

# Автоматически подобрать количество реплик (Horizontal Pod Autoscaler)
kubectl autoscale deployment hello-app --min=2 --max=10 --cpu-percent=80
```

+++
+++
+++

## Работа с подами и контейнерами (для отладки)

Учитывая твой бэкграунд как core-разработчика, эти команды пригодятся, чтобы «залезть внутрь» и проверить окружение/бинарники/конфигурацию.

```bash
# Зайти в shell контейнера (если в нём есть sh/bash)
kubectl exec -it <pod-name> -- sh
# или bash, если есть:
kubectl exec -it <pod-name> -- bash

# Выполнить одну команду в контейнере
kubectl exec <pod-name> -- ls /app

# Перезапустить под (проще, чем удалять вручную — деплоймент сам создаст новый)
kubectl rollout restart deployment hello-app

# Посмотреть историю ревизий деплоймента (полезно для откатов)
kubectl rollout history deployment hello-app

# Сделать откат к предыдущей ревизии
kubectl rollout undo deployment hello-app
```

+++
+++
+++

## Сеть и доступ (важно именно для microk8s)

```bash
# Проброс порта (самый простой способ получить доступ к сервису локально)
kubectl port-forward svc/hello-service 8080:80
# После этого curl http://localhost:8080 работает

# Если нужно пробросить порт конкретного пода
kubectl port-forward pod/<pod-name> 8080:80

# Проверить, что сервис виден по имени внутри кластера (через DNS-аддон)
# Запускаешь временный под с curl/dig и делаешь запрос
kubectl run curl --rm -it --image=curlimages/curl -- sh
```

+++
+++
+++

## Фильтры, селекторы, JSONPath (для автоматизации и скриптов)

Это особенно полезно, когда ты проектируешь системы и хочешь быстро выцепить нужные данные (например, IP, имена, статусы) для скриптов или пайплайнов.

```bash
# Фильтр по лейблу (например, все поды с app=hello-app)
kubectl get pods -l app=hello-app

# Показать только нужные колонки
kubectl get pods -o custom-columns=NAME:.metadata.name,STATUS:.status.phase

# JSONPath (вытащить, например, IP всех подов)
kubectl get pods -o jsonpath="{.items[*].status.podIP}"

# YAML всего ресурса (чтобы посмотреть, что реально создано в кластере)
kubectl get deployment hello-app -o yaml
```
