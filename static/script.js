document.addEventListener("DOMContentLoaded", function () {
  const roleSelect = document.getElementById("role");
  const panel = document.getElementById("skills-panel");
  const list = document.getElementById("skills-list");
  const submitBtn = document.getElementById("analyze-btn");

  if (!roleSelect) return;

  roleSelect.addEventListener("change", function () {
    const roleId = roleSelect.value;
    if (!roleId) {
      panel.classList.remove("visible");
      submitBtn.style.display = "none";
      return;
    }

    fetch(`/api/role/${roleId}`)
      .then((r) => r.json())
      .then((data) => {
        list.innerHTML = "";
        data.skills.forEach((skill) => {
          const row = document.createElement("div");
          row.className = "skill-row";
          row.innerHTML = `
            <div>
              <div class="skill-name">${skill.name}</div>
              <div class="skill-weight">Importance: ${skill.importance}/5</div>
            </div>
            <select name="skill_${skill.id}">
              <option value="not_known">Not known</option>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          `;
          list.appendChild(row);
        });
        panel.classList.add("visible");
        submitBtn.style.display = "inline-block";
      });
  });
});
