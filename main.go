package main

import (
	"encoding/json"
	"log"
	"net/http"
	"sync"
)

type Question struct {
	ID   int    `json:"id"`
	Text string `json:"text"`
	Type string `json:"type"`
}

type Answer struct {
	QuestionID int    `json:"questionId"`
	Value      string `json:"value"`
}

type AnswersRequest struct {
	Answers []Answer `json:"answers"`
}

var questions = []Question{
	{ID: 1, Text: "Как вас зовут?", Type: "text"},
	{ID: 2, Text: "Сколько вам лет?", Type: "number"},
	{ID: 3, Text: "Ваш любимый язык программирования?", Type: "text"},
	{ID: 4, Text: "Готовы учить Go глубже?", Type: "text"},
}

type answerStore struct {
	mu      sync.Mutex
	answers []AnswersRequest
}

func (s *answerStore) save(req AnswersRequest) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.answers = append(s.answers, req)
}

func main() {
	store := &answerStore{answers: make([]AnswersRequest, 0)}

	mux := http.NewServeMux()

	mux.HandleFunc("GET /questions", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, questions)
	})

	mux.HandleFunc("POST /answers", func(w http.ResponseWriter, r *http.Request) {
		var req AnswersRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "invalid JSON payload", http.StatusBadRequest)
			return
		}

		store.save(req)
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})

	fs := http.FileServer(http.Dir("./static"))
	mux.Handle("/", fs)

	addr := ":8080"
	log.Printf("Server started on http://localhost%s\n", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatal(err)
	}
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(payload); err != nil {
		log.Printf("write json error: %v", err)
	}
}
