document.addEventListener("DOMContentLoaded", function () {

    // Clicked icon
    const icon = document.getElementById("logo")

    icon.addEventListener("click", function(e){
        e.stopPropagation();

        window.location.href = "/";

    })


    // Hamburguer menu
    const hamburger = document.getElementById("hamburguerBtn");
    const nav = document.getElementById("nav-header");
    const overlay = document.getElementById("menuOverlay");

    function openMenu() {
        nav.classList.add("active");
        overlay.classList.add("active");
    }

    function closeMenu() {
        nav.classList.remove("active");
        overlay.classList.remove("active");
    }

    hamburger.addEventListener("click", function (e) {
        e.stopPropagation();

        if (nav.classList.contains("active")) {
            closeMenu();
        } else {
            openMenu();
        }
    });

    overlay.addEventListener("click", closeMenu);

    window.addEventListener("scroll", closeMenu);

    document.querySelectorAll(".nav-link").forEach(link => {
        link.addEventListener("click", closeMenu);
    });


});

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