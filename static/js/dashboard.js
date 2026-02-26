/**
 * Dashboard JavaScript
 * Integrates with localStorage data from archive.js
 */

document.addEventListener("DOMContentLoaded", () => {
    // Get data from localStorage (set by archive.js)
    const data = JSON.parse(localStorage.getItem("analysisData"));

    if (!data) {
        console.log("Nenhum dado encontrado.");
        alert("Nenhum dado encontrado.");
        window.location.href = "/";
        return;
    }

    const info = data.player_info;
    const stats = data.geral_matchs;

    // -------- PLAYER INFO --------
    const playerNameElement = document.getElementById("player-name");
    if (playerNameElement) {
        playerNameElement.innerText = `${info.name}#${info.tag} (${info.region})`;
    }

    // -------- KPIs --------
    const wins = stats.matchResult.total_win;
    const losses = stats.matchResult.total_loss;
    const totalGames = wins + losses;

    // Win Rate
    const winrateElement = document.getElementById("winrate");
    if (winrateElement) {
        winrateElement.innerText = stats.matchResult.win_rate + "%";
    }

    // Win/Loss
    const winLossElement = document.getElementById("win-loss");
    if (winLossElement) {
        winLossElement.innerText = `${wins} / ${losses}`;
    }

    // KDA Ratio
    const kdaElement = document.getElementById("kda");
    if (kdaElement) {
        kdaElement.innerText = stats.kda.kda_ratio.toFixed(1);
    }

    // KDA Detail
    const kdaDetailElement = document.getElementById("kda-detail");
    if (kdaDetailElement) {
        kdaDetailElement.innerText = `${stats.kda.avg_kills.toFixed(1)} / ${stats.kda.avg_deaths.toFixed(1)} / ${stats.kda.avg_assists.toFixed(1)}`;
    }

    // Total Games
    const totalGamesElement = document.getElementById("total-games");
    if (totalGamesElement) {
        totalGamesElement.innerText = totalGames;
    }

    // Average Gold
    const avgGoldElement = document.getElementById("avg-gold");
    if (avgGoldElement) {
        avgGoldElement.innerText = Math.round(stats.economy.avg_gold).toLocaleString();
    }

    // Total Gold
    const totalGoldElement = document.getElementById("total-gold");
    if (totalGoldElement) {
        totalGoldElement.innerText = stats.economy.total_gold.toLocaleString();
    }

    // Average Damage
    const avgDamageElement = document.getElementById("avg-damage");
    if (avgDamageElement) {
        avgDamageElement.innerText = Math.round(stats.damage.avg).toLocaleString();
    }

    // Total Damage
    const totalDamageElement = document.getElementById("total-damage");
    if (totalDamageElement) {
        totalDamageElement.innerText = stats.damage.total.toLocaleString();
    }

    // Average Farm
    const avgFarmElement = document.getElementById("avg-farm");
    if (avgFarmElement) {
        avgFarmElement.innerText = stats.farm.avg;
    }

    // Total Farm
    const totalFarmElement = document.getElementById("total-farm");
    if (totalFarmElement) {
        totalFarmElement.innerText = stats.farm.total.toLocaleString();
    }

    // Average Vision
    const avgVisionElement = document.getElementById("avg-vision");
    if (avgVisionElement) {
        avgVisionElement.innerText = stats.vision.avg;
    }

    // Total Vision
    const totalVisionElement = document.getElementById("total-vision");
    if (totalVisionElement) {
        totalVisionElement.innerText = stats.vision.total.toLocaleString();
    }

    // Multikills
    const doubleKillsElement = document.getElementById("double-kills");
    if (doubleKillsElement) {
        doubleKillsElement.innerText = stats.multikills.double;
    }

    const tripleKillsElement = document.getElementById("triple-kills");
    if (tripleKillsElement) {
        tripleKillsElement.innerText = stats.multikills.triple;
    }

    const quadraKillsElement = document.getElementById("quadra-kills");
    if (quadraKillsElement) {
        quadraKillsElement.innerText = stats.multikills.quadra;
    }

    const pentaKillsElement = document.getElementById("penta-kills");
    if (pentaKillsElement) {
        pentaKillsElement.innerText = stats.multikills.penta;
    }

});