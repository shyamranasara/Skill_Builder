"""
java_mcq.py — Java & Spring Boot Backend MCQs with 20-question batch queue.
Covers Java Core, Spring Boot, Hibernate, Microservices, Spring Security & more.
"""

import streamlit as st
from utils.gemini_service import generate_mcq_set, is_api_configured
from utils.question_hash import save_hash, get_question_hash, get_total_seen, clear_topic_history
from utils.mcq_helper import render_question_card, render_feedback, render_score_badge
from utils.firebase_service import record_answers_batch, get_topic_score, log_page_visit

log_page_visit("Java Backend MCQs")

PAGE = "java"
BATCH_SIZE = 20

TOPICS = {
    "☕ Java Core": "Java Core concepts for backend developer interviews: OOP principles (encapsulation, inheritance, polymorphism, abstraction), interfaces vs abstract classes, Java memory model (heap, stack, metaspace), garbage collection (G1, ZGC), generics and type erasure, Java Collections Framework (ArrayList vs LinkedList, HashMap vs TreeMap, HashSet), Comparable vs Comparator, String immutability and String pool, try-with-resources, checked vs unchecked exceptions",

    "🌊 Java 8+ Features": "Java 8 and modern Java features for developer interviews: lambda expressions, functional interfaces (Predicate, Function, Consumer, Supplier), Stream API (map, filter, reduce, collect, flatMap, distinct, sorted, limit), Optional class, method references, default methods in interfaces, CompletableFuture, var keyword, records, sealed classes, pattern matching in Java 16-21",

    "⚡ Java Concurrency": "Java Concurrency and multithreading for backend developer interviews: Thread lifecycle, Runnable vs Callable, ExecutorService and thread pools, synchronized keyword, volatile keyword, ReentrantLock, ReadWriteLock, semaphores, CountDownLatch, CyclicBarrier, BlockingQueue, ConcurrentHashMap, atomic classes (AtomicInteger, AtomicReference), happens-before relationship, deadlock and livelock detection and prevention, virtual threads (Project Loom)",

    "🍃 Spring Boot": "Spring Boot for backend developer interviews: Spring Boot auto-configuration and starter dependencies, dependency injection and IoC container, @Bean vs @Component vs @Service vs @Repository, @RestController and @RequestMapping, request lifecycle, Spring Boot Actuator, application.properties vs application.yml, profiles (@Profile), Spring Boot testing (@SpringBootTest, @WebMvcTest, @DataJpaTest), Spring Boot DevTools",

    "🗄️ Spring Data JPA & Hibernate": "Spring Data JPA and Hibernate for backend developer interviews: JPA entity lifecycle (transient, managed, detached, removed), @Entity, @Table, @Id, @GeneratedValue, relationship mappings (@OneToOne, @OneToMany, @ManyToMany, @ManyToOne), fetch types (LAZY vs EAGER), JPQL vs native queries, criteria API, N+1 query problem and solutions, Hibernate caching (first-level, second-level), transaction management (@Transactional), Spring Data JPA repository methods",

    "🔒 Spring Security": "Spring Security for backend developer interviews: authentication vs authorization, Spring Security filter chain, JWT token authentication, OAuth2 and OpenID Connect, @PreAuthorize and @PostAuthorize, CSRF protection, CORS configuration, password encoding (BCrypt), UserDetails and UserDetailsService, method-level security, Spring Security with Spring Boot 3.x",

    "🏗️ Microservices & Architecture": "Microservices architecture for Java backend developer interviews: microservices vs monolith, service communication (REST, gRPC, message queues), service discovery (Eureka, Consul), API gateway (Spring Cloud Gateway), circuit breaker pattern (Resilience4j), distributed tracing (Zipkin, Jaeger), saga pattern, CQRS, event sourcing, Spring Cloud Config, load balancing (Ribbon, Spring Cloud LoadBalancer)",

    "🐳 Docker & DevOps for Java": "Docker and DevOps concepts for Java backend developer interviews: Dockerfile for Spring Boot apps, multi-stage builds, docker-compose for local development, Kubernetes deployments for Spring Boot (Deployment, Service, ConfigMap, Secret), JVM tuning in containers (memory limits, heap sizing), Maven and Gradle build tools, CI/CD pipeline for Java applications, JVM flags and performance tuning",
}

# ── Page Header ────────────────────────────────────────────────────────────────
st.markdown("""
<h1 style='font-size:2.2rem; background:linear-gradient(90deg,#F59E0B,#EF4444);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;'>
☕ Java & Spring Boot MCQs</h1>
<p style='color:#9CA3AF;'>Java Core · Spring Boot · Hibernate · Microservices · Spring Security · 20 questions per set</p>
""", unsafe_allow_html=True)

# Tech badges
st.markdown("""
<div style='display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:1rem;'>
<span style='background:#F59E0B22;color:#FCD34D;padding:4px 12px;border-radius:20px;font-size:0.8rem;border:1px solid #F59E0B44;'>☕ Java 8-21</span>
<span style='background:#6DB33F22;color:#86EFAC;padding:4px 12px;border-radius:20px;font-size:0.8rem;border:1px solid #6DB33F44;'>🍃 Spring Boot 3.x</span>
<span style='background:#59666C22;color:#94A3B8;padding:4px 12px;border-radius:20px;font-size:0.8rem;border:1px solid #59666C44;'>🗄️ Hibernate/JPA</span>
<span style='background:#EF444422;color:#FCA5A5;padding:4px 12px;border-radius:20px;font-size:0.8rem;border:1px solid #EF444444;'>🏗️ Microservices</span>
<span style='background:#3B82F622;color:#93C5FD;padding:4px 12px;border-radius:20px;font-size:0.8rem;border:1px solid #3B82F644;'>🐳 Docker/K8s</span>
</div>
""", unsafe_allow_html=True)

if not is_api_configured():
    st.warning("⚠️ **Gemini API key not set.** Add key to `.streamlit/secrets.toml`")
    st.stop()

# ── Topic & Settings ───────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    topic_label = st.selectbox("📌 Topic", list(TOPICS.keys()), key=f"{PAGE}_topic")
    topic = TOPICS[topic_label]
with col2:
    difficulty = st.select_slider(
        "🎯 Difficulty", options=["easy", "medium", "hard"], value="medium", key=f"{PAGE}_diff"
    )
with col3:
    q_type = st.radio("Type", ["Single", "Multi"], key=f"{PAGE}_qtype", horizontal=True)
    q_type_val = "single" if q_type == "Single" else "multi"

# ── Sidebar Stats ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📊 Session Stats")
    s = get_topic_score(topic_label)
    if s["total"] > 0:
        st.metric("Correct", f"{s['correct']}/{s['total']}", f"{s['correct']/s['total']*100:.0f}%")
        st.progress(s["correct"] / s["total"])
    else:
        st.info("No questions answered yet")
    st.markdown("---")
    st.metric("🔢 Unique Qs seen", get_total_seen())
    if st.button("🗑️ Reset topic history", use_container_width=True):
        clear_topic_history(topic_label)
        st.success("Cleared!")

# ── Session State Keys ─────────────────────────────────────────────────────────
Q_KEY       = f"{PAGE}_queue"
ANSWERED_KEY= f"{PAGE}_answered"
ANSWER_KEY  = f"{PAGE}_user_ans"
TOPIC_KEY   = f"{PAGE}_ltopic"
DIFF_KEY    = f"{PAGE}_ldiff"
TYPE_KEY    = f"{PAGE}_ltype"

def _queue():   return st.session_state.get(Q_KEY, [])

if (st.session_state.get(TOPIC_KEY) != topic_label or
        st.session_state.get(DIFF_KEY) != difficulty or
        st.session_state.get(TYPE_KEY) != q_type_val):
    for k in [Q_KEY, ANSWERED_KEY, ANSWER_KEY]:
        st.session_state.pop(k, None)
    st.session_state.update({TOPIC_KEY: topic_label, DIFF_KEY: difficulty, TYPE_KEY: q_type_val})

st.markdown("---")
queue = _queue()

if not queue:
    gen_col, _ = st.columns([2, 3])
    with gen_col:
        if st.button(f"🎯 Generate {BATCH_SIZE} Questions", use_container_width=True, type="primary"):
            with st.spinner(f"Generating {BATCH_SIZE} Java/Spring Boot questions..."):
                qs, err = generate_mcq_set(
                    topic, difficulty, q_type_val,
                    count=BATCH_SIZE,
                    prompt_template="java",
                )
            if err:
                st.error(f"❌ {err}")
            elif qs:
                st.session_state.update({Q_KEY: qs, ANSWERED_KEY: False, ANSWER_KEY: {}})
                st.rerun()

    st.markdown("""
    <div style='text-align:center;color:#4B5563;padding:2rem;'>
    <p style='font-size:1.1rem;'>👆 Click to load 20 Java/Spring Boot questions</p>
    <p style='font-size:0.82rem;'>Tailored for real backend developer interviews</p>
    </div>""", unsafe_allow_html=True)
else:
    total = len(queue)
    submitted = st.session_state.get(ANSWERED_KEY, False)
    saved_answers = st.session_state.get(ANSWER_KEY, {})

    if submitted:
        correct_count = 0
        for idx, q in enumerate(queue):
            ans = saved_answers.get(idx)
            correct = q.get("correct", [])
            is_correct = False
            if ans:
                if isinstance(ans, list):
                    is_correct = sorted(ans) == sorted(correct)
                else:
                    is_correct = ans in correct
            if is_correct:
                correct_count += 1
        
        st.markdown("### 🏆 Exam Results")
        render_score_badge(correct_count, total)
        st.markdown("---")

    user_answers = {}
    for idx, q in enumerate(queue):
        st.markdown(f"#### 📝 Question {idx+1} of {total}")
        st.markdown(f"<span style='background:#2D2D4A;color:#F59E0B;padding:4px 12px;border-radius:20px;font-size:0.8rem;'>🏷️ {q.get('keyword','')}</span>", unsafe_allow_html=True)
        st.markdown("")

        prev_ans = saved_answers.get(idx)
        ans = render_question_card(q, key_prefix=f"{PAGE}_q{idx}", disabled=submitted, default_val=prev_ans)
        user_answers[idx] = ans

        if submitted:
            render_feedback(q, prev_ans)
        
        st.markdown("<div style='margin-bottom:2rem;'></div>", unsafe_allow_html=True)

    st.markdown("---")
    submit_col, reset_col = st.columns(2)
    
    if not submitted:
        with submit_col:
            if st.button("📝 Submit Exam", type="primary", use_container_width=True):
                results = []
                for idx, q in enumerate(queue):
                    ans = user_answers[idx]
                    correct = q.get("correct", [])
                    is_correct = False
                    if ans:
                        if isinstance(ans, list):
                            is_correct = sorted(ans) == sorted(correct)
                        else:
                            is_correct = ans in correct
                    
                    results.append(is_correct)
                    h = get_question_hash(q["question"], q["correct"])
                    save_hash(topic_label, h, q.get("keyword", ""))
                
                record_answers_batch(topic_label, results)
                
                st.session_state[ANSWER_KEY] = user_answers
                st.session_state[ANSWERED_KEY] = True
                st.rerun()
        with reset_col:
            if st.button("🗑️ Discard & Load New Set", use_container_width=True):
                st.session_state[Q_KEY] = []
                st.session_state[ANSWERED_KEY] = False
                st.session_state[ANSWER_KEY] = {}
                st.rerun()
    else:
        with submit_col:
            st.info("Exam submitted! Answers and explanations are shown under each question.")
        with reset_col:
            if st.button("🔄 Generate New Exam Set", type="primary", use_container_width=True):
                st.session_state[Q_KEY] = []
                st.session_state[ANSWERED_KEY] = False
                st.session_state[ANSWER_KEY] = {}
                st.rerun()
