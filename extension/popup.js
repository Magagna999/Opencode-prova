const btn = document.getElementById("btn");
const esito = document.getElementById("esito");

if (btn && esito) {
  btn.addEventListener("click", () => {
    esito.textContent = "Pulsante premuto!";
  });
}
