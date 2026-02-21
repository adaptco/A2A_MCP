
import { HumanMessage } from 'https://cdn.jsdelivr.net/npm/@langchain/core/dist/messages.js';
import { ChatGoogleGenerativeAI } from 'https://cdn.jsdelivr.net/npm/@langchain/google-genai/dist/chat_models.js';

document.addEventListener('DOMContentLoaded', () => {
    // Fidelity Monitor Chart
    const fidelityChartCtx = document.getElementById('fidelityChart').getContext('2d');
    const fidelityData = [0.05, 0.052, 0.051, 0.053, 0.054, 0.055, 0.054, 0.053, 0.052, 0.051, 0.050];
    const fidelityChart = new Chart(fidelityChartCtx, {
        type: 'line',
        data: {
            labels: ['T-10', 'T-9', 'T-8', 'T-7', 'T-6', 'T-5', 'T-4', 'T-3', 'T-2', 'T-1', 'T-0'],
            datasets: [{
                label: 'Deviation (u)',
                data: fidelityData,
                borderColor: '#2563EB',
                tension: 0.1
            }]
        },
        options: {
            scales: {
                y: {
                    suggestedMin: 0.045,
                    suggestedMax: 0.060
                }
            }
        }
    });

    // Resonance Radar Chart
    const resonanceRadarChartCtx = document.getElementById('resonanceRadarChart').getContext('2d');
    const resonanceData = [8, 7, 9, 6, 8];
    const resonanceRadarChart = new Chart(resonanceRadarChartCtx, {
        type: 'radar',
        data: {
            labels: ['Math Rigor', '90s Grit', 'Material Utilization', 'Social Flow', 'Kochi Stress Tensors'],
            datasets: [{
                label: 'Resonance',
                data: resonanceData,
                backgroundColor: 'rgba(217, 119, 6, 0.2)',
                borderColor: '#D97706',
                pointBackgroundColor: '#D97706',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: '#D97706'
            }]
        },
        options: {
            scales: {
                r: {
                    suggestedMin: 0,
                    suggestedMax: 10
                }
            }
        }
    });

    // Sovereign Intelligence Hub
    const generateDebriefButton = document.getElementById('generate-debrief');
    const debriefOutput = document.getElementById('debrief-output');

    generateDebriefButton.addEventListener('click', async () => {
        debriefOutput.textContent = 'Generating software artifact...';

        const prompt = document.getElementById('prompt-input').value;

        try {
            const response = await fetch('/agent', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ prompt }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            debriefOutput.textContent = result;

        } catch (error) {
            debriefOutput.textContent = 'Error generating artifact: ' + error.message;
        }
    });
});
