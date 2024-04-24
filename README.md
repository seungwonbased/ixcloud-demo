# ⛅️ KINX IXcloud Kubernetes 3-Tier 아키텍처 배포 👨🏽‍💻
### 실습 기간

- 2024.04.23~2024.04.24

### 실습 인원

- 배승원

### 실습 목표

- IXcloud IKS(쿠버네티스 서비스)에 3-Tier 아키텍처 배포
- Frontend (Client) - Backend (Application) - Database (Data)

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

```
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@ WARNING: UNPROTECTED PRIVATE KEY FILE! @
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
Permissions 0644 for 'ix-db-key-pair.pem' are too open.
It is required that your private key files are NOT accessible by others.
This private key will be ignored. 
Load key "ix-db-key-pair.pem": 
bad permissions [ubuntu@1.201.166.28](mailto:ubuntu@1.201.166.28): Permission denied (publickey).
```

→ 이런 메세지가 발생

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

### 여러 이슈

1. CloudR1에서 쿠버네티스가 사용 불가능
    - 매뉴얼에도 이 내용을 찾을 수 없었음 (내가 못찾은 것일 수도 있음)
    - 그래서 처음부터 다시 함
2. DB 인스턴스 생성 후 SSH 접속 시 오류
    - 키 페어의 권한이 너무 널널했음
    - chmod 600 (소유자의 읽기 및 쓰기) 명령으로 해결
3. DB 서버 구축
    - AWS RDS에 비교하면, 직접 DB 서버를 설치해야 하니 설정해야 할 것이 더 많았음
    - PostgreSQL의 설정 파일에서 Listen addresses를 바꾸거나, Local connections도 설정해줌
4. 쿠버네티스의 kubectl 도구를 로컬에 구성
    - AWS CLI와 같은 도구 없이 직접 원격 kubectl을 구성하기 위해 마스터 노드에 SSH 접속 후 kubeconfig 파일을 다운로드 받아 로컬에 직접 구성 후 컨텍스트 스위치해 사용
5. 백엔드 애플리케이션을 클러스터에 배포 시 ErrImagePull 발생
    - 처음에는 보안 그룹 문제인가 싶어서 확인해보니 egress 트래픽이 모두 열려있었고, 이미지를 Pull 해오는 것은 HTTPS(443)를 사용할테니 문제 없었음
    - 로컬 머신이 ARM 아키텍처의 맥이라 클러스터와 호환되지 않았던 것
        - —platform linux/AMD64 플래그로 x86에 맞게 리빌드
6. CORS 오류
    - 분명 백엔드 애플리케이션에서 CORS 허용을 해놓았는데, CORS 오류 발생
    - 프론트엔드 애플리케이션 개발 시 URL 끝에 슬래시를 붙이지 않아 Redirect 됨
        - Preflight Request가 적절히 처리되지 않았기 때문
    - 애플리케이션 코드 내 URL 끝에 슬래시를 붙여 해결

### IXcloud의 경쟁력

- 프로젝트를 하면서 느낀점
	- **안정적인 서비스**
		- 리소스가 금방 생성되고, 안정적이었음
    - **엔지니어에게 조금 더 자율성이 주어지는 클라우드**
        - 이전에 AWS EKS나 RDS와 같은 완전 관리형 서비스를 사용했을 때, 원하지 않는 업데이트나 패치, 심지어는 인터페이스가 Deprecated여서 당황했던 적이 있음
        - IXcloud는 조금 더 자율성이 보장되어 이런 부분에서 자유롭다고 느낌
    - **개인화된 고객 경험**
        - 리소스를 생성하고 프로젝트를 진행하던 도중, IXcloud 측에서 전화가 와서 프로젝트 목적이 무엇인지와 같은 요소를 세세하게 파악해줌
        - 이런 경험이 추후에 고객 지원을 사용한다면 더 신뢰가고 신속할 것이라는 느낌을 받음
        - 또한 매니지드 서비스들이 맞춤형으로 구성이 가능하기 때문에 기술자가 없는 고객이더라도 클라우드 인프라를 이용할 수 있음
    - **비용 효율성**
        - RDS와 같은 관리형 서비스 대신 직접 구축하는 것이 그렇게 난이도가 높지도 않고, 만약 고객사에 관련 인력이 있다면 이와 같은 방법으로 직접 구축해 사용한다면 비용 효율성을 달성할 수 있을 것

- 이외의 경쟁력
    - **OpenStack 기반**
        - OpenStack은 커뮤니티도 활발하고, 평가가 안좋았던 예전과 달리 사례도 많아지고 기술이 성숙해지면서 긍정적인 평가를 받고 있음
        - 오픈소스이기 때문에 라이센스 비용도 없고, 기술 표준을 따르기 때문에 고객에게 벤더 종속성이라는 리스크를 줄여줄 수 있음
        - OpenStack은 유연하기 때문에 고객의 다양한 환경에 맞춰 조정도 가능
    - **국내 회사의 클라우드**
        - 로컬 벤더라는 점에서, 공공 사업이나 데이터 주권이 민감한 비즈니스에서는 규정을 더 잘 준수할 수 있음
        - 필요하면 더 신속하고 세세하게 현장 지원을 받을 수 있음
    - **CloudHub 서비스 (멀티 클라우드 구성 플랫폼)**
        - AWS, Azure를 비롯해서 국내의 IXcloud, NCP까지 다양한 클라우드를 연결하는 플랫폼을 제공해 필요에 따라 멀티, 하이브리드 클라우드 아키텍처를 구축하고 모니터링 할 수 있음