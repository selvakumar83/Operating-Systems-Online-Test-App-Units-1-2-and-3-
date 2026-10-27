# Operating Systems Reasoning MCQ App

This Streamlit application contains **45 scenario-based MCQs** prepared from the two supplied Operating Systems PDFs.

## Question sets
- Unit 1: 15 questions on OS services, process states/PCB, scheduling, shell conditions, `fork()`/`wait()`, and turnaround/waiting-time reasoning.
- Unit 2: 15 questions on ordinary pipes, IPC, threads, race conditions, semaphores, `test_and_set()`, and compare-and-swap.
- Unit 3: 15 questions on deadlock conditions, dining philosophers, and Banker's safety algorithm.

Every question has four options, one keyed answer, and a concise explanation. The `answer_key.csv` file provides the correct options and explanations for instructor review.

## Run locally
1. Install Python 3.10 or later.
2. Open a terminal in this folder.
3. Run `python -m pip install -r requirements.txt`.
4. Run `python -m streamlit run app.py`.

`run_app.bat` is also provided for Windows.

## Source fidelity
The questions are based on the attached **ISA1 (GSet-2)** and **Level 1 Problem-2 (Unit 2)** documents. The ISA1 PDF covers process/scheduling and synchronization topics; Level 1 Problem-2 covers producer-consumer semaphores, pipes, Banker's algorithm, and dining philosophers. Unit 3 in this app groups deadlock/resource-allocation questions supported by those materials. The PDFs do not supply a separate memory-management syllabus, so memory-management questions have not been invented and attributed to them.

## Important
The answer key and calculations have been checked against the stated assumptions in each question. Please review the question bank before using it for a graded examination.
