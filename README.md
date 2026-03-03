# BWT_Neural-Ninjas# AI Behavioural Threat Detection System

Team: Neural Ninjas
Theme: Cyber Threat Detection Systems

## Problem Statement

Organizations rely heavily on digital infrastructure to manage sensitive information and operational workflows. Traditional cybersecurity solutions primarily focus on detecting external attacks such as malware, phishing, and network intrusions, but they often fail to detect insider threats caused by legitimate users misusing authorized access.

Suspicious behaviors such as unusual login times, excessive file access, repeated failed login attempts, abnormal data transfers, and unauthorized device usage frequently go unnoticed because they do not match predefined attack signatures.

## Solution Overview

This project proposes an AI-based Behavioural Threat Detection System that monitors and analyzes user behavior patterns instead of relying solely on signature-based detection.

The system collects user activity logs, processes them through a feature engineering pipeline, and applies machine learning techniques to identify deviations from normal behavioral patterns. By detecting anomalies in real time, the system enables proactive identification of potential insider threats before significant damage occurs.

## System Architecture

The system consists of the following modules:

* User Activity Logging Module
* Data Collection Layer
* Feature Engineering Module
* Anomaly Detection Engine (Isolation Forest)
* Risk Scoring Module
* Alert and Monitoring Dashboard

User activity data such as login timestamps, file access frequency, authentication attempts, and device usage details are collected and transformed into structured features.

A machine learning model based on the Isolation Forest algorithm analyzes these features to detect abnormal behavior. The model assigns anomaly scores, which are processed by a dynamic risk scoring system. If the calculated risk exceeds a predefined threshold, real-time alerts are generated and displayed on an administrative dashboard.

## Technologies Used

* Python
* Pandas
* Scikit-learn
* Flask (for dashboard, optional)
* GitHub

## Key Features

* Behavior-based monitoring
* AI-powered anomaly detection
* Dynamic risk scoring
* Real-time alert generation
* Scalable and modular architecture

## Future Enhancements

* Cloud-based deployment
* Email/SMS alert integration
* Advanced behavioral profiling
* Role-based risk assessment
* Interactive analytics dashboard
