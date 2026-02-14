const form = document.getElementById("survey-form");
const statusNode = document.getElementById("status");

async function loadQuestions() {
  statusNode.textContent = "Загрузка вопросов...";
  try {
    const response = await fetch("/questions");
    if (!response.ok) {
      throw new Error("Не удалось получить вопросы");
    }

    const questions = await response.json();
    renderQuestions(questions);
    statusNode.textContent = "";
  } catch (error) {
    statusNode.textContent = "Ошибка загрузки вопросов";
  }
}

function renderQuestions(questions) {
  form.innerHTML = "";

  questions.forEach((question) => {
    const wrapper = document.createElement("div");
    wrapper.className = "question";

    const label = document.createElement("label");
    label.setAttribute("for", `q-${question.id}`);
    label.textContent = question.text;

    const input = document.createElement("input");
    input.id = `q-${question.id}`;
    input.name = String(question.id);
    input.type = question.type === "number" ? "number" : "text";
    input.required = true;

    wrapper.append(label, input);
    form.appendChild(wrapper);
  });

  const submitButton = document.createElement("button");
  submitButton.type = "submit";
  submitButton.textContent = "Отправить";
  form.appendChild(submitButton);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  statusNode.textContent = "";

  const formData = new FormData(form);
  const answers = [];

  for (const [questionId, value] of formData.entries()) {
    answers.push({
      questionId: Number(questionId),
      value: String(value),
    });
  }

  try {
    const response = await fetch("/answers", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ answers }),
    });

    if (!response.ok) {
      throw new Error("Ошибка отправки");
    }

    statusNode.textContent = "Спасибо!";
    form.reset();
  } catch (error) {
    statusNode.textContent = "Не удалось отправить ответы";
  }
});

loadQuestions();
