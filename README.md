NexusCart
High-Concurrency Distributed E-Commerce Platform
<div align="center"> <i>A microservices demonstration project with integrated machine learning recommendations</i> </div>
✦ Overview
NexusCart is a code demonstration platform showcasing distributed system patterns in e-commerce. Built with Java microservices and a Python ML pipeline, it implements production-grade architectural patterns including event-driven design, atomic inventory operations, and real-time personalization.

✦ Technology Stack
Backend · Spring Boot 3.1 · Spring Cloud · PostgreSQL · Redis · Kafka · Elasticsearch
ML Pipeline · Faust · PySpark · Feast · XGBoost · LightFM · FastAPI
Infrastructure · Docker · Kubernetes · Terraform · Prometheus · Grafana · ELK

✦ Core Services
User · JWT authentication · profile management
Product · catalog · search · categories
Inventory · Redis stock control · warehouse tracking
Order · state machine · sharded database · idempotent creation
Payment · Stripe integration · webhooks · refunds
Promotion · Lua atomic scripts · flash sales · token bucket

Recommendation · real-time behavior processing · feature store (Feast) · XGBoost/LightFM models · FastAPI serving · AB testing framework

<div align="center"> <sub>Code demonstration · patterns not performance tested</sub> </div>
