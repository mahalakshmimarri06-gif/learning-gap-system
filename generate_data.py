"""Run once: python generate_data.py  -> creates the 3 CSV files in data/"""
import random, urllib.parse
import pandas as pd

random.seed(7)
TOPICS = {
    "DBMS": ["Normalization", "SQL Joins", "Transactions", "Indexing"],
    "OS": ["Deadlocks", "CPU Scheduling", "Paging", "Synchronization"],
    "DSA": ["Trees", "Graphs", "Sorting", "Dynamic Programming"],
    "CN": ["Subnetting", "TCP", "Routing", "HTTP"],
}
NAMES = ["Ananya","Bhavya","Charitha","Divya","Eesha","Farah","Gayathri","Harini","Ishita","Jahnavi",
         "Keerthi","Lasya","Meghana","Nikitha","Om","Pranavi","Qureshi","Rohini","Sneha","Tanvi",
         "Uma","Vaishnavi","Waseem","Yamini","Zoya","Aarav","Bhargav","Chaitanya","Deepak","Eshwar",
         "Farhan","Girish","Harsha","Imran","Jayanth","Kiran","Lokesh","Manoj","Naveen","Pavan"]

# 1) scores
rows = []
for i, name in enumerate(NAMES):
    sid = f"CS{i+1:03d}"
    ability = random.uniform(45, 90)
    all_topics = [(s, t) for s, ts in TOPICS.items() for t in ts]
    weak = random.sample(all_topics, random.choice([2, 3, 4]))
    for s, t in all_topics:
        for q in range(2):
            base = ability - (28 if (s, t) in weak else 0) + (6 if q == 1 else 0)
            pct = max(5, min(100, random.gauss(base, 9)))
            rows.append([sid, name, s, t, round(pct / 10, 1), 10,
                         f"2026-0{8 + q}-{random.randint(1, 28):02d}"])
pd.DataFrame(rows, columns=["student_id","name","subject","topic","marks_obtained","max_marks","quiz_date"]
             ).to_csv("data/sample_scores.csv", index=False)

# 2) resources (search links so they never break)
res = []
for s, ts in TOPICS.items():
    for t in ts:
        q = urllib.parse.quote_plus(f"{t} {s} explained")
        res.append([s, t, f"{t} - video lecture", f"https://www.youtube.com/results?search_query={q}", "video"])
        res.append([s, t, f"{t} - GeeksforGeeks", f"https://www.geeksforgeeks.org/search/?q={urllib.parse.quote_plus(t)}", "article"])
        res.append([s, t, f"{t} - NPTEL courses", f"https://nptel.ac.in/courses?search={urllib.parse.quote_plus(t)}", "course"])
pd.DataFrame(res, columns=["subject","topic","title","url","type"]).to_csv("data/resources.csv", index=False)

# 3) question bank: subject, topic, question, a, b, c, d, correct, difficulty
Q = [
("DBMS","Normalization","Which normal form removes partial dependency?","1NF","2NF","3NF","BCNF","B","easy"),
("DBMS","Normalization","A table is in 3NF if it is in 2NF and has no ___ dependency.","partial","transitive","multivalued","join","B","medium"),
("DBMS","SQL Joins","Which join returns all rows from the left table and matches from the right?","INNER JOIN","LEFT JOIN","CROSS JOIN","SELF JOIN","B","easy"),
("DBMS","SQL Joins","A CROSS JOIN of tables with 4 and 5 rows returns how many rows?","9","20","5","4","B","medium"),
("DBMS","Transactions","Which ACID property ensures all-or-nothing execution?","Atomicity","Consistency","Isolation","Durability","A","easy"),
("DBMS","Transactions","Dirty read happens when a transaction reads data that is ___.","committed","uncommitted","deleted","indexed","B","medium"),
("DBMS","Indexing","Which structure is most commonly used for database indexes?","Stack","B+ Tree","Queue","Heap","B","easy"),
("DBMS","Indexing","A clustered index determines the ___ of the table rows.","physical order","column type","foreign keys","views","A","medium"),
("OS","Deadlocks","Which is NOT a necessary condition for deadlock?","Mutual exclusion","Hold and wait","Preemption","Circular wait","C","easy"),
("OS","Deadlocks","Banker's algorithm is used for deadlock ___.","detection","avoidance","ignoring","recovery","B","medium"),
("OS","CPU Scheduling","Which scheduling algorithm can cause starvation?","Round Robin","FCFS","Priority scheduling","None","C","easy"),
("OS","CPU Scheduling","Shortest Job First is optimal for minimizing average ___ time.","waiting","burst","arrival","response","A","medium"),
("OS","Paging","Paging eliminates which type of fragmentation?","Internal","External","Both","Neither","B","easy"),
("OS","Paging","Which page replacement algorithm suffers from Belady's anomaly?","LRU","Optimal","FIFO","None","C","medium"),
("OS","Synchronization","A semaphore that takes only 0 or 1 is called a ___ semaphore.","counting","binary","named","timed","B","easy"),
("OS","Synchronization","The critical section problem requires mutual exclusion, progress and ___.","bounded waiting","deadlock","paging","caching","A","medium"),
("DSA","Trees","Inorder traversal of a BST gives elements in ___ order.","random","sorted","reverse","level","B","easy"),
("DSA","Trees","Max number of nodes in a binary tree of height h (root at height 0)?","2^h","2^(h+1)-1","h^2","2h","B","medium"),
("DSA","Graphs","Which data structure does BFS use?","Stack","Queue","Heap","Tree","B","easy"),
("DSA","Graphs","Dijkstra's algorithm fails for graphs with ___ edges.","negative weight","directed","dense","weighted","A","medium"),
("DSA","Sorting","Worst-case time complexity of Quick Sort?","O(n log n)","O(n)","O(n^2)","O(log n)","C","easy"),
("DSA","Sorting","Which sort is stable and has O(n log n) worst case?","Quick Sort","Heap Sort","Merge Sort","Selection Sort","C","medium"),
("DSA","Dynamic Programming","DP is applicable when a problem has overlapping subproblems and ___.","greedy choice","optimal substructure","randomness","recursion only","B","easy"),
("DSA","Dynamic Programming","Time complexity of 0/1 knapsack DP (n items, capacity W)?","O(n)","O(nW)","O(2^n)","O(W)","B","medium"),
("CN","Subnetting","How many usable hosts are in a /24 network?","256","254","255","250","B","easy"),
("CN","Subnetting","Subnet mask for /26 is?","255.255.255.192","255.255.255.128","255.255.255.224","255.255.255.240","A","medium"),
("CN","TCP","TCP connection establishment uses a ___ handshake.","2-way","3-way","4-way","1-way","B","easy"),
("CN","TCP","Which TCP mechanism prevents the sender from overwhelming the receiver?","Congestion control","Flow control","Routing","Checksum","B","medium"),
("CN","Routing","Which is a distance-vector routing protocol?","OSPF","RIP","BGP","IS-IS","B","easy"),
("CN","Routing","OSPF is based on which algorithm?","Bellman-Ford","Dijkstra","Prim","Kruskal","B","medium"),
("CN","HTTP","Which HTTP status code means 'Not Found'?","200","301","404","500","C","easy"),
("CN","HTTP","Which HTTP method is idempotent and used to replace a resource?","POST","PUT","PATCH","CONNECT","B","medium"),
]
pd.DataFrame(Q, columns=["subject","topic","question","option_a","option_b","option_c","option_d","correct_option","difficulty"]
             ).to_csv("data/question_bank.csv", index=False)
print("Created data/sample_scores.csv, data/resources.csv, data/question_bank.csv")
