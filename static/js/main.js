document.getElementById("playerForm").addEventListener("submit", async function(e) {
    e.preventDefault();

    const playerName = document.getElementById("playerName").value;
    const playerTag = document.getElementById("playerTag").value;
    const region = document.getElementById("region").value;

    document.getElementById("loading").style.display = "block";

    const response = await fetch("/analyze", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            playerName,
            playerTag,
            region
        })
    });

    console.log(response)

    const data = await response.json();

    localStorage.setItem("analysisData", JSON.stringify(data));

    window.location.href = "/dashboard";
});