pipeline {
  agent { label 'ubuntu-latest' }
  environment {
    DEPLOY_CHANNEL = "${env.DEPLOY_CHANNEL ?: 'production'}"
  }
  stages {
    stage('Checkout') {
      steps { checkout scm }
    }
    stage('Tooling') {
      steps {
        sh '''
          sudo apt-get update -y
          sudo apt-get install -y jq moreutils curl python3 || true
          python3 --version && jq --version || true
          sha256sum --version || true
        '''
      }
    }
    stage('Install renderer (optional)') {
      when { expression { return env.RENDERER_URL?.trim() } }
      steps {
        withCredentials([string(credentialsId: 'renderer-url', variable: 'RENDERER_URL')]) {
          sh 'curl -L "$RENDERER_URL" -o ./render && chmod +x ./render'
        }
      }
    }
    stage('Deploy') {
      steps {
        sh '''
          chmod +x ./deploy.sh
          ./deploy.sh "$DEPLOY_CHANNEL"
        '''
      }
    }
    stage('Collect artifacts') {
      steps {
        sh '''
          mkdir -p artifacts
          cp -r storage/ledger.jsonl artifacts/ || true
          cp -r ops/boo/avatar/guard/out artifacts/out || true
          cp -r /tmp/* artifacts/ 2>/dev/null || true
        '''
      }
    }
  }
  post {
    always {
      archiveArtifacts artifacts: 'artifacts/**', fingerprint: true, onlyIfSuccessful: false
    }
  }
}
