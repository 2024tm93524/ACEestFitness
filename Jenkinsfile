// Jenkinsfile – Declarative Pipeline for ACEest Fitness
// This tells Jenkins what to do when it pulls your code

pipeline {

    // Run on any available Jenkins agent (worker)
    agent any

    // ─────────────────────────────────────────────
    // PIPELINE STAGES
    // ─────────────────────────────────────────────
    stages {

        stage('Checkout') {
            steps {
                echo '=== Pulling latest code from GitHub ==='
                checkout scm
            }
        }

        stage('Setup Python Environment') {
            steps {
                echo '=== Installing Python dependencies ==='
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Lint Check') {
            steps {
                echo '=== Running flake8 syntax check ==='
                sh '''
                    . venv/bin/activate
                    pip install flake8
                    flake8 app.py --select=E9,F63,F7,F82 --show-source
                '''
            }
        }

        stage('Unit Tests') {
            steps {
                echo '=== Running Pytest unit tests ==='
                sh '''
                    . venv/bin/activate
                    pytest tests/ -v --tb=short
                '''
            }
        }

        stage('Docker Build') {
            steps {
                echo '=== Building Docker image ==='
                sh 'docker build -t aceest-fitness:latest .'
            }
        }
    }

    // ─────────────────────────────────────────────
    // POST-BUILD ACTIONS
    // ─────────────────────────────────────────────
    post {
        success {
            echo '✅ BUILD SUCCESSFUL – All stages passed!'
        }
        failure {
            echo '❌ BUILD FAILED – Check the logs above for errors.'
        }
        always {
            echo '=== Pipeline finished ==='
        }
    }
}
