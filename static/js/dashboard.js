document.addEventListener("DOMContentLoaded", () => {

    const data = JSON.parse(sessionStorage.getItem("analysisData"));

    if (!data) {

        console.log(data)

        alert("Nenhum dado encontrado.");
        window.location.href = "/";
        return;
    }

    const info = data.player_info;
    const stats = data.geral_matchs;

    // -------- PLAYER INFO --------
    document.getElementById("player-info").innerText =
        `${info.name}#${info.tag} (${info.region})`;

    // -------- KPIs --------
    const wins = stats.matchResult.total_win;
    const losses = stats.matchResult.total_loss;
    const totalGames = wins + losses;

    document.getElementById("winrate").innerText =
        stats.matchResult.win_rate + "%";

    document.getElementById("kda").innerText =
        stats.kda.kda_ratio;

    document.getElementById("total-games").innerText =
        totalGames;

    document.getElementById("gold").innerText =
        stats.economy.total_gold.toLocaleString();

    // -------- WIN / LOSS CHART --------
    new Chart(document.getElementById("winChart"), {
        type: "doughnut",
        data: {
            labels: ["Wins", "Losses"],
            datasets: [{
                data: [wins, losses]
            }]
        }
    });

    // -------- FARM CHART --------
    new Chart(document.getElementById("farmChart"), {
        type: "bar",
        data: {
            labels: ["Total CS", "Average CS"],
            datasets: [{
                data: [
                    stats.farm.total,
                    stats.farm.avg
                ]
            }]
        }
    });

    // -------- VISION CHART --------
    new Chart(document.getElementById("visionChart"), {
        type: "bar",
        data: {
            labels: ["Total Vision", "Average Vision"],
            datasets: [{
                data: [
                    stats.vision.total,
                    stats.vision.avg
                ]
            }]
        }
    });

});
