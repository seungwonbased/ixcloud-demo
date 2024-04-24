# ⛅️ KINX IXcloud Kubernetes 3-Tier 아키텍처 배포 👨🏽‍💻
### 실습 기간

- 2024.04.23~2024.04.24

### 실습 인원

- 배승원

### 실습 목표

- IXcloud IKS(쿠버네티스 서비스)에 3-Tier 아키텍처 배포

### 프로젝트 생성

IXcloud 존: CloudR1, CloudR2 있음

→ CloudR1 선택, CloudR2는 쿠버네티스 지원 안함! (이걸 한참 뒤에 알았다…)

### 멤버 추가

- 마스터, 정산, 일반 중에 선택
- 활성화, 알림 수신 설정 가능

### 네트워크 생성

- CIDR: 192.168.10.0/24
- 1개의 서브넷 자동 생성됨

### DB 인스턴스 생성

- 사양: 1코어 1기가
- 볼륨: 기본 50기가 이외에 추가하지 않음
- 시간당 요금제 (26원)
- OS: Ubuntu 20.04
- ssh를 위한 키페어 생성
- 생성한 네트워크와 서브넷 선택
- 사용자 정의 스크립트 안 씀
- 보안 그룹 default

|방향|ether 타입|IP 프로토콜|Port 범위|
|---|---|---|---|
|ingress|IPv6|전체|전체|
|egress|IPv6|전체|전체|
|ingress|IPv4|전체|전체|
|egress|IPv4|전체|전체|

→ 인스턴스 엄청 금방 뜸

### 공인 IP 생성

- 공인 IP 생성 후 DB 인스턴스에 연결

### ssh를 위한 보안 그룹 생성

- ingress
    - port 22
    - everywhere (0.0.0.0)
- egress
    - 모든 포트
    - everywhere (0.0.0.0)

### ssh 접속

- 키페어 있는 위치에서

```bash
ssh -i ix-db-key-pair.pem ubuntu@1.201.166.28
```

@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

@ WARNING: UNPROTECTED PRIVATE KEY FILE! @

@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

Permissions 0644 for 'ix-db-key-pair.pem' are too open.

It is required that your private key files are NOT accessible by others.

This private key will be ignored. 

Load key "ix-db-key-pair.pem": 
bad permissions [ubuntu@1.201.166.28](mailto:ubuntu@1.201.166.28): Permission denied (publickey).

→ 이런 메세지가 뜸

- SSH 키 파일의 권한 설정이 너무 널널하게 설정되어 있어서 발생
- SSH 키 파일은 보안상의 이유로 다른 사용자에게 읽히거나 수정될 수 없어야 함
- 이를 해결하기 위해, 해당 키 파일의 권한을 조정

```bash
chmod 600 ix-db-key-pair.pem
ssh -i ix-db-key-pair.pem ubuntu@1.201.166.28
```

### 우분투 root 계정 비밀번호 변경

```bash
sudo -i
passwd root
```

- 패스워드는 password로 설정함

### DB 인스턴스에 postgresql 22.04 설치

```bash
# 시스템 업데이트
sudo apt update
sudo apt upgrade

# postgresql 설치
sudo apt install postgresql postgresql-contrib

# postgresql은 기본적으로 외부 접속이 불가능
# 외부 접속 허용으로 변경
sudo vi /etc/postgresql/12/main/postgresql.conf
# -> listen_addresses='*'로 변경

sudo vi /etc/postgresql/12/main/pg_hba.conf
# -> IPv4 local connections에서 host의 ADDRESS를 0.0.0.0/0으로 변경

# postgresql 재시작
sudo service postgresql restart

# 서비스 되고있나 확인
sudo systemctl status postgresql.service
netstat -nap|grep 5432

# postgresql 사용자 설정
sudo -i -u postgres

# postgresql 프롬프트 접속
psql

# 데이터베이스 생성
CREATE DATABASE dummy;
ALTER USER postgres WITH PASSWORD 'password';

# 나가기
exit
```

### DB 접근을 위한 보안 그룹 설정

- ingress
    - port 5432
    - everywhere (0.0.0.0)

### 백엔드 애플리케이션 개발 및 도커화

- Framework: Flask
- /dummies에 POST 메서드로 오는 문자열을 DB에 저장하는 프로그램
- Dockerfile

```dockerfile
FROM ubuntu:20.04

WORKDIR /dummy

COPY . /dummy

RUN apt-get update -y
RUN apt-get install -y libpq-dev
RUN apt-get install -y python3-dev
RUN apt-get install -y python3
RUN apt-get install -y python3-pip

RUN pip install wheel
RUN pip install -r ./requirements.txt

ENV FLASK_APP=app
ENV FLASK_DEBUG=true
ENV APP_CONFIG_FILE=/dummy/config/config.py
ENV DB_USER=postgres
ENV DB_PASSWORD=password
ENV DB_HOST=1.201.166.28
ENV DB_PORT=5432
ENV DB_NAME=dummy

RUN chmod +x ./app.sh

CMD ./app.sh
```

- 빌드 및 Docker Hub에 푸시

```bash
docker build -t seungwonbased/ix-dummy:1.0 .

docker push seungwonbased/ix-dummy:1.0
```

### 프론트엔드 애플리케이션 개발 및 도커화

- Framework: React
- 인풋에 문자열을 입력하고 제출하면 POST 메서드로 백엔드에 전송하는 프로그램
- Dockerfile 빌더 패턴 사용

```dockerfile
FROM node AS builder
WORKDIR /dummy
COPY package.json .
RUN npm install
COPY . .
RUN npm run build

FROM nginx AS runtime
COPY --from=builder /dummy/build /usr/share/nginx/html/
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d
CMD [ "nginx", "-g", "daemon off;" ]
```

- Nginx 설정 파일

```conf
server {
    listen 80;
    location / {
        root        /usr/share/nginx/html/;
        index       index.html;
        try_files   $uri $uri/ /index.html;
    }
}
```

### 쿠버네티스 클러스터 생성 (IKS)

- 클러스터
    - 버전 1.23.7
    - CNI types: calico
    - 키 페어 생성
    - DB 인스턴스랑 같은 네트워크, 서브넷
        - 서비스 네트워크: 10.233.0.0/18
        - 파드 네트워크: 10.233.64.0/18
- 노드 그룹
    - 사양: 2코어 2기가 (시간 당 56원)
    - 워커 개수: 1
- 오토 스케일러 미사용

### kubectl 내 로컬 머신에 구성

- 마스터 노드 접속
    - 커넥터 노드 보안 그룹 22번 포트 열기
    - 키 페어로 ssh 접속
- 마스터 노드의 kubeconfig 확인

```bash
cat ~/.kube/config
```

→ - cluster, - context, - name 복사

- 로컬 머신의 kubeconfig 수정

```bash
vi ~./kube/config
```

→ - cluster, - context, - name 수정

→ - cluster의 server 부분 커넥터 노드 IP로 변경!!!

- 로컬 머신의 kubectl 컨텍스트 전환

```bash
kubectl config get-contexts
kubectl config use-context <컨텍스트 이름>
```

- kubectl 사용을 위한 마스터 노드 보안 그룹에 ingress 6443 허용

### 백엔드 배포

```yaml
# flask.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: deploy-flask
spec:
  selector:
    matchLabels:
      app: flask
  replicas: 1
  template:
    metadata:
      labels:
        app: flask
    spec:
      containers:
      - name: ix-flask
        image: docker.io/seungwonbased/ix-flask:1.0
        ports:
        - containerPort: 5000
---
apiVersion: v1
kind: Service
metadata:
  name: service-flask
spec:
  selector:
    app: flask
  ports:
  - protocol: TCP
    port: 5000
    targetPort: 5000
    nodePort: 30000
  type: NodePort
```

- ErrImagePull 에러 발생
    - kubectl describe po <pod 이름>
    - 도커 허브에서 https(443)으로 이미지 끌어오니까 egress는 모두 열려있으므로 보안 그룹 문제는 아님
    - 로컬 머신이 arm 아키텍처고 클러스터는 x86이라 안되는 것일 수도…!!!
- Dockerfile 변경

```dockerfile
FROM ubuntu:20.04

WORKDIR /dummy

COPY . /dummy

# Hash Sum mismatch 에러 때문에 이 라인 추가함
RUN sed -i 's/archive.ubuntu.com/kr.archive.ubuntu.com/g' /etc/apt/sources.list
RUN apt-get update -y
RUN apt-get install -y libpq-dev
RUN apt-get install -y python3-dev
RUN apt-get install -y python3
RUN apt-get install -y python3-pip

RUN pip install wheel
RUN pip install -r ./requirements.txt

ENV FLASK_APP=app
ENV FLASK_DEBUG=true
ENV APP_CONFIG_FILE=/dummy/config/config.py
ENV DB_USER=postgres
ENV DB_PASSWORD=password
ENV DB_HOST=1.201.172.251
ENV DB_PORT=5432
ENV DB_NAME=dummy

RUN chmod +x ./app.sh

CMD ./app.sh
```

- 도커 이미지 x86으로 다시 빌드

```bash
docker build --platform linux/amd64 -t seungwonbased/ix-flask:1.0 .
docker push seungwonbased/ix-flask:1.0
```

- 다시 배포

```bash
kubectl apply -f flask.yaml
```

- 백엔드 통신을 위한 보안 그룹 설정
    - 워커 노드의 30000번 ingress 포트 열기
    - 워커 노드의 80 포트 열기

### 프론트엔드

```yaml
# react.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: deploy-react
spec:
  selector:
    matchLabels:
      app: react
  replicas: 1
  template:
    metadata:
      labels:
        app: react
    spec:
      containers:
      - name: ix-react
        image: docker.io/seungwonbased/ix-react:1.0
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: service-react
spec:
  selector:
    app: react
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
    nodePort: 30001
  type: NodePort
```

- 도커 이미지 x86으로 빌드 후 푸시
- 배포
- 사용자 - 웹 서버 통신을 위한 보안 그룹 설정
    - 워커 노드의 30001번 포트 열기

### 테스트

![](https://github.com/seungwonbased/ixcloud-demo/blob/main/assets/1.png)
![](https://github.com/seungwonbased/ixcloud-demo/blob/main/assets/2.png)
- NodePort로 열어둔 주소에 접속
- 테스트 데이터 전송

![](https://github.com/seungwonbased/ixcloud-demo/blob/main/assets/3.png)
- 통신 성공

![](https://github.com/seungwonbased/ixcloud-demo/blob/main/assets/4.png)
- 백엔드 로그

![](https://github.com/seungwonbased/ixcloud-demo/blob/main/assets/5.png)
- DB 인스턴스 접속 후 프롬프트로 데이터 확인

### 성공!!! 🎉
