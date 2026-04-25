pipeline {
    agent any

    environment {
        IMAGE_NAME = "aceest-fitness"
        BUILD_TAG  = "v1.${BUILD_NUMBER}"
    }

    stages {

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

        // SonarQube scans the source code for bugs, vulnerabilities, and code quality issues
        // This runs before Docker build so only quality-approved code is deployed
        stage('SonarQube Analysis') {
            environment {
                // This pulls the scanner using the Name field from your screenshot
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

        stage('Docker Build & Tag') {
            steps {
                echo "=== Building Docker image: ${IMAGE_NAME}:${BUILD_TAG} ==="
                sh '''
                    docker build -t ${IMAGE_NAME}:${BUILD_TAG} -t ${IMAGE_NAME}:latest .
                    echo "=== Images built and tagged ==="
                    docker images | grep ${IMAGE_NAME}
                '''
            }
        }

        // ── Pytest INSIDE the Docker container ──────────────────────
        // Assignment requires: "Execute Pytest inside containerized environment"
        // This runs tests using the BUILT IMAGE, not the local venv
        // Proves the container itself works correctly end-to-end
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
        // ────────────────────────────────────────────────────────────

        stage('Deploy Latest Image') {
            steps {
                echo '=== Stopping old container and deploying latest ==='
                sh '''
                    docker stop aceest-app 2>/dev/null || true
                    docker rm aceest-app 2>/dev/null || true

                    # Kill ANY other container holding port 5000
                    CONFLICT=$(docker ps --filter "publish=5000" --format "{{.ID}}")
                    if [ -n "$CONFLICT" ]; then
                        echo "Found container occupying port 5000 — stopping it..."
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
                            docker rm   aceest-app 2>/dev/null || true
                            docker run -d \
                                --name aceest-app \
                                -p 5000:5000 \
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

        // ── Kubernetes Deployment (Rolling Update) ──────────────────
        // Deploys to Docker Desktop's built-in Kubernetes cluster
        // Uses Rolling Update strategy by default (pods replaced 1 by 1)
        // All other strategies (blue-green, canary etc) are applied
        // manually via kubectl for demonstration purposes
        stage('Kubernetes Deploy') {
            steps {
                echo '=== Deploying to Kubernetes (Docker Desktop) ==='
                sh '''
                    # Check kubectl is available
                    if ! command -v kubectl &> /dev/null; then
                        echo "=== kubectl not found - skipping K8s deploy ==="
                        exit 0
                    fi

                    # Check Kubernetes cluster is reachable
                    if ! kubectl cluster-info &> /dev/null; then
                        echo "=== Kubernetes not running ==="
                        echo "=== Enable it: Docker Desktop → Settings → Kubernetes ==="
                        exit 0
                    fi

                    # Apply the main deployment (Rolling Update strategy)
                    kubectl apply -f k8s/deployment.yaml

                    # Wait for rollout to complete
                    kubectl rollout status deployment/aceest-fitness --timeout=60s

                    # Show running pods and service
                    echo "=== Running Kubernetes pods ==="
                    kubectl get pods -l app=aceest-fitness

                    echo "=== Kubernetes service ==="
                    kubectl get service aceest-service
                '''
            }
        }
        // ────────────────────────────────────────────────────────────
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
