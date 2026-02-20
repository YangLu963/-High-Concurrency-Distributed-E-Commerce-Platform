NexusCart
⚡ High-Concurrency Distributed E-Commerce Platform
<div align="center"> <code>microservices · event-driven · ml recommendations · cloud-native</code> </div>
<div align="center"> <img src="https://img.shields.io/badge/java-17-red?style=for-the-badge&logo=java"/> <img src="https://img.shields.io/badge/spring-6.0-green?style=for-the-badge&logo=spring"/> <img src="https://img.shields.io/badge/python-3.10-blue?style=for-the-badge&logo=python"/> <img src="https://img.shields.io/badge/kafka-white?style=for-the-badge&logo=apachekafka"/> <img src="https://img.shields.io/badge/kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white"/> </div>
🎯 Project Overview
A code demonstration platform showcasing distributed system patterns in e-commerce

NexusCart implements production-grade architectural patterns including event-driven design, atomic inventory operations, and real-time personalization. Built with Java microservices and a Python ML pipeline, this project demonstrates how modern e-commerce platforms are architected.

🏗️ Architecture Layers
<table> <tr> <td width="33%" align="center"> <h3>☕ <b>Core Services</b></h3> <p><i>Java · Spring Boot</i></p> <p>User · Order · Payment</p> </td> <td width="33%" align="center"> <h3>📊 <b>Data Services</b></h3> <p><i>Java · Spring Boot</i></p> <p>Product · Inventory · Promotion</p> </td> <td width="33%" align="center"> <h3>🧠 <b>ML Services</b></h3> <p><i>Python · FastAPI</i></p> <p>Pipeline · Feature Store · Models</p> </td> </tr> </table>
🛠️ Technology Stack
☕ Backend Services
text
Spring Boot 3.1  •  Spring Cloud  •  PostgreSQL  •  Redis  •  Kafka  •  Elasticsearch
Resilience4j     •  Redisson       •  Caffeine    •  JWT   •  OAuth2
🐍 ML Pipeline
text
Kafka + Faust    •  PySpark        •  Feast       •  XGBoost  •  LightFM  •  FastAPI
SHAP             •  Jupyter        •  Pandas      •  Statsmodels
☁️ Infrastructure
text
Docker           •  Kubernetes     •  Terraform   •  Jenkins  •  Prometheus  •  Grafana
Helm             •  ELK Stack      •  SkyWalking  •  Jaeger
📦 Core Services Breakdown
<table> <tr> <th width="120">Service</th> <th>Responsibilities</th> <th width="150">Tech</th> </tr> <tr> <td><b>👤 User</b></td> <td>Authentication · JWT · Profiles · Address Book</td> <td><code>Spring Security</code></td> </tr> <tr> <td><b>📦 Product</b></td> <td>Catalog · Categories · Search · Attributes</td> <td><code>Elasticsearch</code></td> </tr> <tr> <td><b>📊 Inventory</b></td> <td>Stock Management · Redis Atomic Ops · Reservations</td> <td><code>Redis + Lua</code></td> </tr> <tr> <td><b>📝 Order</b></td> <td>State Machine · Sharding · ID Generation · History</td> <td><code>ShardingSphere</code></td> </tr> <tr> <td><b>💳 Payment</b></td> <td>Stripe Integration · Webhooks · Refunds</td> <td><code>Stripe API</code></td> </tr> <tr> <td><b>🏷️ Promotion</b></td> <td>Flash Sales · Lua Scripts · Token Bucket · Coupons</td> <td><code>Redis Locks</code></td> </tr> </table>


🛠️ Technology Stack
☕ Backend Services
Spring Boot 3.1 · Spring Cloud · PostgreSQL · Redis · Kafka · Elasticsearch
Resilience4j · Redisson · Caffeine · JWT · OAuth2

🐍 ML Pipeline
Kafka + Faust · PySpark · Feast · XGBoost · LightFM · FastAPI
SHAP · Jupyter · Pandas · Statsmodels

☁️ Infrastructure
Docker · Kubernetes · Terraform · Jenkins · Prometheus · Grafana
Helm · ELK Stack · SkyWalking · Jaeger

📦 Core Services
👤 User Service
Authentication · JWT tokens · Profile management · Address book
Spring Security · PostgreSQL

📦 Product Service
Catalog management · Categories · Search · Attributes
Elasticsearch · Redis cache

📊 Inventory Service
Stock control · Redis atomic operations · Warehouse tracking · Reservations
Redis + Lua scripts

📝 Order Service
State machine · Database sharding · ID generation · Order history
ShardingSphere · Kafka events

💳 Payment Service
Stripe integration · Webhook handling · Refund processing
Stripe API · Resilience4j

🏷️ Promotion Service
Flash sales · Lua atomic scripts · Token bucket · Coupon management
Redis locks · Scheduled tasks

🧠 Recommendation System
Data Pipeline

Real-time stream processing with Kafka and Faust consumes user behavior events as they happen, generating session-based features. Batch processing with PySpark runs daily ETL jobs on historical data, building user profiles and item similarity matrices.

Feature Store

Built with Feast, the feature store serves as the central repository for all ML features. User features include demographics and behavior patterns. Item features include categories, price ranges, and popularity metrics. All features are cached in Redis for low-latency access during inference.

Model Layer

XGBoost models predict CTR by learning complex nonlinear feature interactions. LightFM provides hybrid collaborative filtering, combining user-item interactions with content features. Both models are served through FastAPI REST endpoints with Prometheus monitoring.

Experimentation

The AB testing framework consistently assigns users to experiment buckets and tracks interactions to calculate statistical significance between control and treatment groups. Jupyter notebooks enable deep-dive analysis of experiment results.

🔄 Key Workflows
⚡ Flash Sale Flow

When a user clicks buy during a flash sale, the request hits the API gateway for authentication and rate limiting. The promotion service validates the user's token and executes a Redis Lua script that atomically checks and deducts inventory. If successful, the order service creates an order in pending payment status and publishes an OrderCreatedEvent to Kafka.

The payment service consumes this event and initiates payment processing through Stripe. The user is redirected to complete payment. Stripe sends a webhook notification when payment completes, which is verified and processed by the payment service. A PaymentResultEvent is published, consumed by the order service to update order status to paid and by the inventory service to confirm the final inventory deduction.

If any step fails, compensating actions are triggered. Payment failure leads to order cancellation and inventory release. Timeout mechanisms automatically cancel unpaid orders after fifteen minutes.

🎯 Recommendation Flow

User interactions such as product views, clicks, and purchases are captured and published to Kafka in real-time. The Faust consumer processes these events, updates real-time user features, and stores them in the feature store.

When a user visits the homepage or product listing page, the frontend calls the recommendation API. The model serving service retrieves the user's features from the feature store, along with candidate item features. Multiple recall strategies execute in parallel, including collaborative filtering, content-based matching, and popular item fallback. The recalled items pass through ranking models that predict CTR and CVR, producing a final scored list returned to the client.

The recommendations display to the user, and their interactions with recommended items are tracked, closing the feedback loop for continuous model improvement.
