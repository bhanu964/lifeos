# Contributing to LifeOS

Thank you for your interest in contributing to LifeOS! We welcome contributions that improve multi-agent coordination, voice workflows, security, and developer ergonomics.

---

## Code of Conduct

Please treat all contributors and users with respect, empathy, and constructive feedback.

---

## Development Workflow

1. **Fork the Repository**: Create your own fork on GitHub.
2. **Clone and Branch**:
   ```bash
   git clone https://github.com/your-username/lifeos.git
   cd lifeos
   git checkout -b feature/your-feature-name
   ```
3. **Set Up Environments**:
   Follow instructions in [docs/SETUP.md](docs/SETUP.md) to set up both backend and frontend.
4. **Run Tests**:
   - Backend: `pytest backend/tests/ -v`
   - Frontend: `npm --prefix frontend run build`
5. **Commit Guidelines**:
   Write clear, imperative commit messages (e.g. `feat: add Google Tasks recurring event support`).
6. **Open a Pull Request**:
   Push your branch and open a PR against `main`.

---

## Pre-PR Checklist

- [ ] All 74 existing tests pass cleanly (`pytest backend/tests/`).
- [ ] Frontend builds without TypeScript or Vite errors (`npm --prefix frontend run build`).
- [ ] No API keys, passwords, or secrets are committed.
- [ ] Any new endpoints or configuration variables are documented in `docs/` and `.env.example`.
