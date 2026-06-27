const revealItems = document.querySelectorAll("[data-reveal]");
const navLinks = [...document.querySelectorAll(".nav a")];
const sections = navLinks
  .map((link) => document.querySelector(link.getAttribute("href")))
  .filter(Boolean);

const revealObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        revealObserver.unobserve(entry.target);
      }
    });
  },
  { rootMargin: "0px 0px -10% 0px", threshold: 0.1 },
);

revealItems.forEach((item) => revealObserver.observe(item));

const navObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) {
        return;
      }
      navLinks.forEach((link) => {
        link.classList.toggle("is-active", link.getAttribute("href") === `#${entry.target.id}`);
      });
    });
  },
  { rootMargin: "-35% 0px -55% 0px", threshold: 0 },
);

sections.forEach((section) => navObserver.observe(section));

document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    const target = document.querySelector(button.dataset.copy);
    if (!target) {
      return;
    }
    const originalText = button.textContent;
    try {
      await navigator.clipboard.writeText(target.innerText.trim());
      button.textContent = "Copied";
      window.setTimeout(() => {
        button.textContent = originalText;
      }, 1400);
    } catch {
      button.textContent = "Select JSON";
      window.setTimeout(() => {
        button.textContent = originalText;
      }, 1400);
    }
  });
});
