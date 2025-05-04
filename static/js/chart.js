// static/chart.js

/**
 * Fetches word frequency data from the Flask backend
 * and initializes the Highcharts word cloud chart.
 */
async function createWordCloudChart() {
    try {
        // Fetch data from the Flask endpoint
        const response = await fetch('/data/word_frequency');

        // Check if the fetch was successful
        if (!response.ok) {
            // Try to get error message from response body
            let errorMsg = `Error fetching data: ${response.status} ${response.statusText}`;
            try {
                const errorData = await response.json();
                errorMsg = `Error fetching data: ${errorData.error || response.statusText}`;
            } catch (e) {
                // Ignore if response body is not JSON
            }
            throw new Error(errorMsg);
        }

        // Parse the JSON data from the response
        const data = await response.json();

        // Check if data is empty
        if (!data || data.length === 0) {
            document.getElementById('chart-container').innerHTML = '<p class="p-4 text-center text-red-500">No data available to display the chart.</p>';
            console.warn("No word data received from the server.");
            return; // Stop execution if no data
        }

        // --- Highcharts Configuration ---
        Highcharts.chart('chart-container', {
            // Specify the chart type as 'wordcloud'
            series: [{
                type: 'wordcloud',
                // Assign the fetched data to the series
                data: data,
                // Optional: Name the series (useful for tooltips or legends if needed)
                name: 'Frequency'
            }],
            // Chart Title
            title: {
                text: 'Word Cloud from Palabras_Clave',
                align: 'center'
            },
            // Tooltip configuration (text displayed on hover)
            tooltip: {
                headerFormat: '<span style="font-size: 10px">{point.key}:</span><br/>',
                pointFormat: '<b>{point.weight}</b>' // In this case, weight is always 1
            },
            // Accessibility module enhances chart usability for screen readers etc.
            accessibility: {
                enabled: true, // Keep accessibility enabled
                point: {
                     valueDescriptionFormat: '{point.weight}.' // Describes the point value
                }
            },
            // Optional: Add exporting options (download buttons)
            exporting: {
                buttons: {
                    contextButton: {
                        menuItems: ["viewFullscreen", "printChart", "separator", "downloadPNG", "downloadJPEG", "downloadPDF", "downloadSVG"]
                    }
                }
            },
             // Optional: Styling for the word cloud
             plotOptions: {
                wordcloud: {
                    // Rotation options if desired
                    // rotation: {
                    //    from: -60,
                    //    to: 60,
                    //    orientations: 5
                    // },
                    // Style for individual words
                    style: {
                        fontFamily: 'Inter, sans-serif', // Match body font
                        // fontWeight: 'bold' // Example: make words bold
                    }
                }
            }
            // You can add more Highcharts configuration options here as needed
            // See Highcharts documentation for 'wordcloud' type:
            // https://api.highcharts.com/highcharts/series.wordcloud
        });

    } catch (error) {
        // Display error message in the chart container if fetching or rendering fails
        console.error('Failed to create word cloud chart:', error);
        document.getElementById('chart-container').innerHTML = `<p class="p-4 text-center text-red-500">Could not load chart: ${error.message}</p>`;
    }
}

// --- Execute the chart creation function ---
// Ensure the DOM is fully loaded before trying to create the chart
document.addEventListener('DOMContentLoaded', createWordCloudChart);
