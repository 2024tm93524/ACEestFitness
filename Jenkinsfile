pipeline {
    agent any

    environment {
        IMAGE_NAME = "2024tm93524/aceest-fitness"
        BUILD_TAG  = "v1.${BUILD_NUMBER}"
    }

    stages {

        stage('Install System Dependencies') {
            steps {
                echo '=== Installing system tools (if missing) ==='
                sh '''
                    if ! command -v python3 > /dev/null 2>&1; then
                        echo "Installing Python3..."
                        apt-get update -y -qq
                        apt-get install -y python3 python3-pip python3-venv -qq
                    else
                        echo "Python3 already installed: $(python3 --version)"
                    fi

                    if ! command -v docker > /dev/null 2>&1; then
                        echo "Installing Docker CLI..."
                        apt-get update -y -qq
                        apt-get install -y docker.io -qq
                    else
                        echo "Docker already installed: $(docker --version)"
                    fi

                    if ! command -v kubectl > /dev/null 2>&1; then
                        echo "Installing kubectl..."
                        curl -LO "https://dl.k8s.io/release/v1.36.0/bin/linux/amd64/kubectl" -s
                        install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
                        rm kubectl
                    else
                        echo "kubectl already installed"
                    fi

                    mkdir -p /root/.kube
                    if [ -f /var/jenkins_home/.kube/config ]; then
                        cp /var/jenkins_home/.kube/config /root/.kube/config
                        sed -i "s|https://kubernetes.docker.internal:6443|https://192.168.65.3:6443|g" /root/.kube/config
                        sed -i "s|https://127.0.0.1:6443|https://192.168.65.3:6443|g" /root/.kube/config
                        sed -i "s|https://192.168.65.254:6443|https://192.168.65.3:6443|g" /root/.kube/config
                        echo "kubeconfig ready"
                    fi
                '''
            }
        }

        stage('Checkout') {
            steps {
                echo '=== Pulling latest code from GitHub ==='
                checkout scm
            }
        }

        stage('Setup Python Environment') {
            steps {
                echo '=== Setting up Python virtual environment ==='
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip -q
                    pip install -r requirements.txt -q
                '''
            }
        }

        stage('Lint Check') {
            steps {
                echo '=== Running flake8 syntax check ==='
                sh '''
                    . venv/bin/activate
                    pip install flake8 -q
                    flake8 app.py --select=E9,F63,F7,F82 --show-source
                '''
            }
        }

        stage('Unit Tests') {
            steps {
                echo '=== Running Pytest unit tests ==='
                sh '''
                    . venv/bin/activate
                    pip install pytest pytest-flask -q
                    pytest tests/ -v --tb=short
                '''
            }
        }

        stage('SonarQube Analysis') {
            environment {
                SCANNER_HOME = tool 'aceest_fitness_sonarreport'
            }
            steps {
                echo '=== Running SonarQube static analysis ==='
                withSonarQubeEnv('aceest_fitness_sonarreport') {
                    sh '''
                        . venv/bin/activate
                        $SCANNER_HOME/bin/sonar-scanner \
                          -Dsonar.projectKey=aceest-fitness \
                          -Dsonar.sources=. \
                          -Dsonar.python.version=3 \
                          -Dsonar.sourceEncoding=UTF-8
                    '''
                }
            }
        }

        stage('Docker Build, Tag & Push') {
            steps {
                echo "=== Building and Pushing Docker image: ${IMAGE_NAME}:${BUILD_TAG} ==="
                sh '''
                    docker build -t ${IMAGE_NAME}:${BUILD_TAG} -t ${IMAGE_NAME}:latest .
                    echo "=== Pushing to Docker Hub ==="
                    docker push ${IMAGE_NAME}:${BUILD_TAG}
                    docker push ${IMAGE_NAME}:latest
                    echo "=== Images pushed successfully ==="
                '''
            }
        }

        stage('Test Inside Container') {
            steps {
                echo '=== Running Pytest INSIDE Docker container ==='
                sh '''
                    docker run --rm \
                        -e DB_PATH=/tmp/test.db \
                        ${IMAGE_NAME}:latest \
                        sh -c "pip install pytest pytest-flask -q && pytest tests/ -v --tb=short"
                '''
            }
        }

        stage('Deploy Latest Image') {
            steps {
                echo '=== Stopping old container and deploying latest ==='
                sh '''
                    docker stop aceest-app 2>/dev/null || true
                    docker rm aceest-app 2>/dev/null || true
                    CONFLICT=$(docker ps --filter "publish=5000" --format "{{.ID}}")
                    if [ -n "$CONFLICT" ]; then
                        echo "$CONFLICT" | xargs docker stop
                        echo "$CONFLICT" | xargs docker rm 2>/dev/null || true
                    fi
                    docker run -d \
                        --name aceest-app \
                        -p 5000:5000 \
                        --restart unless-stopped \
                        ${IMAGE_NAME}:latest
                    echo "=== App deployed at http://localhost:5000 ==="
                    docker ps | grep aceest-app
                '''
            }
        }

        stage('Rollback Check') {
            steps {
                echo '=== Verifying deployment health ==='
                sh '''
                    sleep 5
                    if docker ps | grep -q aceest-app; then
                        echo "Deployment SUCCESS - container is healthy"
                        docker ps | grep aceest-app
                    else
                        echo "Container crashed - triggering rollback..."
                        PREV_TAG=$(docker images ${IMAGE_NAME} \
                            --format "{{.Tag}}" \
                            | grep "^v1\\." \
                            | grep -v "^${BUILD_TAG}$" \
                            | sort -t. -k2 -rn \
                            | head -1)
                        if [ -n "$PREV_TAG" ]; then
                            echo "Rolling back to ${IMAGE_NAME}:${PREV_TAG}"
                            docker stop aceest-app 2>/dev/null || true
                            docker rm aceest-app 2>/dev/null || true
                            docker run -d --name aceest-app -p 5000:5000 \
                                --restart unless-stopped \
                                ${IMAGE_NAME}:${PREV_TAG}
                            echo "Rollback complete - running ${PREV_TAG}"
                        else
                            echo "No previous image found for rollback"
                            exit 1
                        fi
                    fi
                '''
            }
        }

        stage('Kubernetes Deploy') {
            steps {
                echo '=== Deploying to Kubernetes (Docker Desktop) ==='
                sh '''
                    if ! command -v kubectl > /dev/null 2>&1; then
                        echo "=== kubectl not found - skipping ==="
                        exit 0
                    fi
                    if ! kubectl cluster-info > /dev/null 2>&1; then
                        echo "=== Kubernetes not reachable - skipping ==="
                        exit 0
                    fi
                    kubectl apply -f k8s/deployment.yaml
                    kubectl rollout status deployment/aceest-fitness --timeout=60s
                    echo "=== Kubernetes pods ==="
                    kubectl get pods -l app=aceest-fitness
                    echo "=== Kubernetes service ==="
                    kubectl get service aceest-service
                '''
            }
        }
    }

    post {
        success {
            echo "BUILD SUCCESSFUL - Deployed ${IMAGE_NAME}:${BUILD_TAG}"
        }
        failure {
            echo "BUILD FAILED - Check the logs above for errors."
        }
        always {
            echo '=== Pipeline finished ==='
            sh 'docker images | grep aceest-fitness || true'
        }
    }
}