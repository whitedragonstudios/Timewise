// ----------------------
// Standalone News Cycle
// ----------------------
function initNewsCycle(newsArticles) {
    let currentIndex = 0;

    function showNews() {
        if (!newsArticles || newsArticles.length === 0) return;

        const news = newsArticles[currentIndex];
        document.getElementById('news-src').textContent = news.src;
        document.getElementById('news-art').textContent = news.art;
        document.getElementById('news-url').href = news.url;

        currentIndex = (currentIndex + 1) % newsArticles.length;
    }

    showNews(); // show first immediately
    return setInterval(showNews, 30000); // cycle every 30s
}

// ----------------------
// Weather Update Function
// ----------------------
function updateWeatherWidget(weatherData) {
    if (!weatherData) return;

    document.querySelector(".sidebar h3").textContent = `${weatherData.city}, ${weatherData.state || ''}${weatherData.state && weatherData.country ? ' - ' : ''}${weatherData.country || ''}`;
    document.querySelector(".sidebar img").src = `/static/weather_icon/${weatherData.icon || 'default.png'}`;
    document.querySelector(".sidebar .weather-row:nth-child(1) .value").textContent = `${weatherData.feel}°F`;
    document.querySelector(".sidebar .weather-row:nth-child(2) .value").textContent = `${weatherData.temp}°F`;
    document.querySelector(".sidebar .weather-row:nth-child(3) .value").textContent = `${weatherData.humid}%`;
    document.querySelector(".sidebar .weather-row:nth-child(4) .value").textContent = `${weatherData.clouds}%`;
    document.querySelector(".sidebar .weather-row:nth-child(5) .value").textContent = weatherData.wind;
}

// ----------------------
// DOMContentLoaded Setup
// ----------------------
document.addEventListener("DOMContentLoaded", () => {
    // --- ID Scan Auto-Submit ---
    const input = document.getElementById("idscan");
    const form = document.getElementById("autoForm");
    const maxLength = 8;

    input.focus();
    input.addEventListener("input", () => {
        if (input.value.length >= maxLength) form.submit();
    });

    // --- News Fetch & Update ---
    let newsCycleInterval;
    async function fetchAndUpdateNews() {
        try {
            const data = await fetch("/refresher/news").then(r => r.json());
            if (newsCycleInterval) clearInterval(newsCycleInterval);
            newsCycleInterval = initNewsCycle(data);
        } catch (error) {
            console.error("Error fetching news:", error);
        }
    }

    fetchAndUpdateNews(); // initial load
    setInterval(fetchAndUpdateNews, 3600000); // every 1 hour

    // --- Weather Fetch & Update ---
    async function fetchAndUpdateWeather() {
        try {
            const weatherData = await fetch("/refresher/weather").then(r => r.json());
            updateWeatherWidget(weatherData);
        } catch (error) {
            console.error("Error fetching weather:", error);
        }
    }

    fetchAndUpdateWeather(); // initial load
    setInterval(fetchAndUpdateWeather, 120 * 60 * 1000); // every 2 hours
});
