# ACEest Fitness & Gym – DevOps CI/CD Pipeline

> **Assignment 1 – Introduction to DevOps (CSIZG514/SEZG514)**  
> ACEest Functional Fitness Management System – Flask Web Application

---

## Project Overview

This repository implements a full DevOps CI/CD pipeline for the **ACEest Fitness & Gym** management web application. The application is built with **Flask (Python)** and the pipeline automates testing, linting, Docker image assembly, and build verification using **GitHub Actions** and **Jenkins**.

---

## Repository Structure

```
aceest-devops/
├── app.py                        ← Main Flask application (all routes & business logic)
├── requirements.txt              ← Python dependencies
├── README.md                     ← This file
├── templates/
│   ├── base.html                 ← Shared HTML layout
│   ├── login.html                ← Login page
│   ├── dashboard.html            ← Main dashboard
│   ├── clients.html              ← Client listing
│   ├── add_client.html           ← Add/update client form
│   ├── client_detail.html        ← Individual client page
│   └── add_workout.html          ← Log workout form
├── tests/
│   └── test_app.py               ← Pytest test suite (30+ tests)
```

---