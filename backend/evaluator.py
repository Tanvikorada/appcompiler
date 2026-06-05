import json
import time
from pipeline import run_pipeline

TEST_PROMPTS = [
    # 10 real product prompts
    "Build a CRM with login, contacts, dashboard, role-based access, and premium plan with payments. Admins can see analytics.",
    "Create a task management app with projects, subtasks, due dates, team collaboration, and Kanban board view.",
    "Build an e-commerce store with product listings, shopping cart, checkout, order history, and admin inventory management.",
    "Create a job board where employers post jobs, applicants apply, and admins moderate listings.",
    "Build a healthcare appointment booking system with doctor profiles, time slots, patient history, and notifications.",
    "Create a learning management system with courses, video lessons, quizzes, certificates, and student progress tracking.",
    "Build a real estate platform with property listings, agent profiles, search filters, and inquiry forms.",
    "Create a restaurant ordering system with menu management, table reservations, and kitchen order display.",
    "Build a social network with user profiles, posts, comments, likes, followers, and direct messaging.",
    "Create a SaaS analytics dashboard with user metrics, revenue charts, cohort analysis, and CSV export.",

    # 10 edge cases
    "Make an app.",                                                                    # vague
    "Build something for my business that does everything I need.",                    # very vague
    "Create an app with login and also without login for some users.",                 # conflicting
    "Build a free app that also charges users monthly.",                               # conflicting
    "Make an app with 500 features including AI, blockchain, and VR.",                # overspecified chaos
    "Build an app.",                                                                   # incomplete
    "Create a platform for users.",                                                    # incomplete
    "Build a Twitter clone but also a LinkedIn clone but also a Shopify clone.",      # conflicting
    "Make an app that is both mobile and desktop and also a TV app and works offline and online.",  # complex constraints
    "Build a platform where users can do anything they want with complete freedom.",    # undefined scope
]


def run_evaluation():
    results = []

    for i, prompt in enumerate(TEST_PROMPTS):
        print(f"Testing prompt {i+1}/20: {prompt[:60]}...")

        start = time.time()
        retries = 0
        success = False
        failure_type = None
        result = {}

        for attempt in range(2):  # max 2 retries
            try:
                result = run_pipeline(prompt)
                latency = time.time() - start

                if result.get("success"):
                    success = True
                    break
                else:
                    retries += 1
                    failure_type = result.get("error", "unknown")
            except Exception as e:
                retries += 1
                failure_type = str(e)
                latency = time.time() - start

        latency = time.time() - start

        results.append({
            "prompt_index": i + 1,
            "prompt_type": "real" if i < 10 else "edge_case",
            "prompt": prompt[:100],
            "success": success,
            "retries": retries,
            "latency_seconds": round(latency, 2),
            "failure_type": failure_type if not success else None,
            "repaired": result.get("repaired", False) if success else False,
        })

    # Metrics
    total = len(results)
    successes = sum(1 for r in results if r["success"])
    avg_latency = sum(r["latency_seconds"] for r in results) / total
    avg_retries = sum(r["retries"] for r in results) / total

    report = {
        "summary": {
            "total_prompts": total,
            "success_rate": f"{(successes/total)*100:.1f}%",
            "avg_latency_seconds": round(avg_latency, 2),
            "avg_retries": round(avg_retries, 2),
            "failure_types": list(set(r["failure_type"] for r in results if r["failure_type"])),
        },
        "results": results,
    }

    with open("../evaluation_results.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nDONE. Success rate: {report['summary']['success_rate']}")
    print(f"Avg latency: {report['summary']['avg_latency_seconds']}s")
    return report


if __name__ == "__main__":
    run_evaluation()
