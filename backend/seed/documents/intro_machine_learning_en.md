# Introduction to Machine Learning — Chapter 1

*(Synthetic demo teaching material for the UniAgent corpus.)*

## 1.1 What is Machine Learning?

Machine learning (ML) is a branch of artificial intelligence that studies
algorithms able to improve their performance on a task through experience,
rather than by following explicitly programmed rules. A widely used working
definition says that a program learns from experience *E* with respect to a
task *T* and a performance measure *P* if its performance on *T*, as measured
by *P*, improves with experience *E*.

Consider spam filtering. Instead of writing thousands of hand-crafted rules
("if the subject contains the word FREE, mark as spam"), we collect a large
set of emails already labeled as *spam* or *not spam* and let an algorithm
discover the statistical patterns that separate the two classes. When new
kinds of spam appear, we retrain the model on fresh data instead of rewriting
the rules.

## 1.2 Types of Machine Learning

**Supervised learning.** The training data consists of input-output pairs:
every example is annotated with the correct answer (a *label*). The goal is to
learn a function that maps new, unseen inputs to correct outputs. Two classic
problem families are:

- *Classification* — the output is a discrete category: spam / not spam,
  disease present / absent, handwritten digit 0-9.
- *Regression* — the output is a continuous value: tomorrow's temperature,
  the price of an apartment, expected electricity demand.

**Unsupervised learning.** The data has no labels; the algorithm must find
structure on its own. Typical tasks are *clustering* (grouping similar
customers by purchasing behavior) and *dimensionality reduction* (compressing
hundreds of correlated features into a few informative ones).

**Reinforcement learning.** An agent interacts with an environment, receives
rewards or penalties, and learns a strategy (policy) that maximizes the
long-term reward. Game playing and robot control are the standard examples.

## 1.3 The Learning Pipeline

A practical ML project usually follows the same skeleton:

1. **Data collection** — gather raw examples relevant to the task.
2. **Feature engineering** — represent each example as a vector of measurable
   properties (features). For an email: word frequencies, sender domain,
   number of links.
3. **Train/test split** — divide the data, for example 80% for training and
   20% for testing. The test set is put aside and never used during training.
4. **Training** — fit the model parameters on the training set.
5. **Evaluation** — measure performance on the held-out test set, which
   estimates how the model will behave on genuinely new data.

The train/test split is the single most important discipline in applied ML.
Evaluating a model on the same data it was trained on is like grading students
on the exact exercises they memorized: the score tells us nothing about real
understanding.

## 1.4 Overfitting and Generalization

A model **overfits** when it learns the noise and accidental quirks of the
training data instead of the underlying pattern. An overfitted model shows
excellent accuracy on training data and poor accuracy on new data. The
opposite failure, **underfitting**, happens when the model is too simple to
capture the pattern at all.

The ability to perform well on unseen data is called **generalization**, and
it is the true goal of learning. Common remedies against overfitting include
using more training data, simplifying the model, *regularization* (penalizing
overly complex solutions), and *cross-validation* (rotating the validation
subset to obtain a more reliable performance estimate).

## 1.5 Evaluation Metrics

For classification, plain *accuracy* (the share of correct predictions) can be
misleading on imbalanced data: a test where 99% of patients are healthy lets a
useless "always healthy" model reach 99% accuracy. More informative metrics
are:

- **Precision** — of all objects predicted positive, how many are truly
  positive;
- **Recall** — of all truly positive objects, how many the model found;
- **F1-score** — the harmonic mean of precision and recall.

For regression, the usual metrics are the *mean squared error* (MSE) and the
*mean absolute error* (MAE), which measure how far predictions deviate from
the true values on average.

## 1.6 Summary

Machine learning replaces hand-written rules with patterns extracted from
data. Supervised learning needs labeled examples, unsupervised learning finds
structure without labels, and reinforcement learning optimizes behavior
through reward. A trustworthy ML workflow always separates training data from
test data and chooses evaluation metrics that match the real task. In the next
chapter we build our first complete model — a linear regressor — and examine
its behavior on a small housing-price dataset.
