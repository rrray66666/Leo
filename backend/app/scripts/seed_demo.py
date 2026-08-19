"""Demo data seed script for the CRM project.

Creates demo users (admin / sales / pm / cs), ~35 customers spread across all
8 sales stages, plus contracts, tasks, communications, payments, stage history,
follow-ups and notifications.

Idempotent: if demo data already exists (e.g. a user with email
demo.admin@crm.com), the script exits gracefully without changing anything.

Run from the backend directory:
    python -m app.scripts.seed_demo
"""

import random
import sys
from datetime import date, datetime, timedelta, timezone

from app.core.security import get_password_hash
from app.database import SessionLocal
from app.models.communication import Communication
from app.models.contract import Contract
from app.models.customer import Customer
from app.models.dict_item import DictItem
from app.models.follow_up import FollowUp
from app.models.notification import Notification
from app.models.payment import Payment
from app.models.stage_history import StageHistory
from app.models.task import Task
from app.models.user import User

DEMO_PASSWORD = "demo123456"
DEMO_ADMIN_EMAIL = "demo.admin@crm.com"

REGIONS = ["Beijing", "Shanghai", "Guangzhou", "Shenzhen", "Hangzhou", "Chengdu", "Wuhan"]
SOURCE_CHANNELS = ["Website", "Referral", "Exhibition", "Cold Call", "Social Media"]
COMM_CHANNELS = ["phone", "wechat", "meeting", "email"]
TASK_PRIORITIES = ["low", "medium", "high", "urgent"]
TASK_NAMES = [
    "需求调研与确认",
    "技术方案设计",
    "系统开发与配置",
    "数据迁移与初始化",
    "用户培训",
    "上线部署",
    "验收测试",
    "售后支持",
]
COMM_CONTENTS = {
    "phone": "电话沟通客户需求，客户重点关注交付周期和售后服务。",
    "wechat": "微信确认方案细节，客户表示需要内部审批后再确认。",
    "meeting": "上门拜访并演示产品方案，客户反馈整体满意，进入商务环节。",
    "email": "邮件发送最新方案资料与报价单，等待客户反馈。",
}
COMM_NEXT_ACTIONS = [
    "跟进客户内部审批进展",
    "安排第二次方案演示",
    "确认报价并推动签约",
    "收集客户补充需求",
    "预约下次回访时间",
]
PAYMENT_TERMS_LIST = [
    "30% deposit, 40% milestone, 30% on delivery",
    "50% deposit, 50% on delivery",
    "20% deposit, 50% milestone, 30% on delivery",
]
CONTRACT_AMOUNTS = [50000, 88000, 120000, 156000, 200000, 260000, 320000, 450000, 580000, 680000, 800000]

# Days stayed in the current stage per stage -> a mix of normal / warning / danger alerts.
# Base/alert thresholds (see app.services.stage_service.STAGES):
#   1: 7/14   2: 14/21   3: 7/14   4: 14/21   5: 30/45   6: 14/21   7: 30/45   8: 0/0
STAGE_STAY_RANGES = {
    1: (3, 40),
    2: (5, 30),
    3: (3, 20),
    4: (5, 30),
    5: (10, 50),
    6: (5, 30),
    7: (10, 50),
    8: (1, 10),
}

# Customers per stage (4-5 per stage, 35 total).
STAGE_COUNTS = {1: 4, 2: 5, 3: 4, 4: 4, 5: 5, 6: 4, 7: 4, 8: 5}

# (company name, contact person)
CUSTOMER_DATA = [
    ("Aurora Tech Co., Ltd.", "Wang Lei"),
    ("Blue Ocean Logistics", "Chen Fang"),
    ("长江教育科技集团", "Zhao Min"),
    ("Green Valley Agriculture", "Sun Li"),
    ("云启软件科技有限公司", "Zhou Qiang"),
    ("Peak Mountain Travel", "Wu Jing"),
    ("中科智能装备有限公司", "Zheng Hao"),
    ("Harbor City Property", "Feng Lan"),
    ("星辰传媒文化有限公司", "Xu Yan"),
    ("Silver River Finance", "Sun Peng"),
    ("东方医疗设备有限公司", "Liang Xin"),
    ("Maple Grove Furniture", "Hu Bin"),
    ("天府食品集团", "Gao Yuan"),
    ("Northern Lights Energy", "Lin Xue"),
    ("华信咨询有限公司", "Deng Chao"),
    ("Crystal Bay Hotel", "Cao Yu"),
    ("青云数据科技有限公司", "Luo Jing"),
    ("Iron Bridge Manufacturing", "Xie Fei"),
    ("绿洲环保工程有限公司", "Han Lei"),
    ("Red Rock Mining", "Tang Wei"),
    ("百川贸易有限公司", "Cui Ning"),
    ("Golden Sun Agriculture", "Shen Jie"),
    ("鹏程建筑集团有限公司", "Yao Chen"),
    ("Cloud Nine E-commerce", "Duan Rui"),
    ("蓝海教育咨询有限公司", "Xiao Wen"),
    ("Starlight Media Group", "Meng Jie"),
    ("恒润精密制造有限公司", "Yuan Bo"),
    ("Pacific Gateway Trading", "Dai Lin"),
    ("康泰健康管理有限公司", "Su Nan"),
    ("Ocean Pearl Seafood", "Fan Rong"),
    ("天穹航空航天科技有限公司", "Jin Liang"),
    ("Sunrise Textiles", "Qiu Hua"),
    ("新桥智能制造有限公司", "Lei Yang"),
    ("Evergreen Nursery", "Luo Han"),
    ("博远生物科技有限公司", "Jiang Tao"),
]


def _build_stage_list() -> list[int]:
    stages: list[int] = []
    for stage, count in STAGE_COUNTS.items():
        stages.extend([stage] * count)
    return stages


def _seed_dict_items(db) -> None:
    """Seed data dictionary items (regions / industries / channels / document categories).

    These back the dropdown lists in the UI; customers reference them by code.
    """
    dict_data = {
        "region": REGIONS,
        "industry": [
            "Technology", "Manufacturing", "Finance", "Healthcare",
            "Education", "Logistics", "Retail", "Energy",
        ],
        "channel": SOURCE_CHANNELS,
        "document_category": ["contract", "requirement", "acceptance", "invoice", "other"],
    }
    for category, names in dict_data.items():
        existing = db.query(DictItem).filter(DictItem.category == category).count()
        if existing:
            continue
        for idx, name in enumerate(names):
            db.add(
                DictItem(
                    category=category,
                    name=name,
                    code=name,
                    sort_order=idx,
                    is_active=True,
                )
            )
    db.commit()
    print("Dictionary items seeded.")


def run() -> None:
    db = SessionLocal()
    try:
        # Seed dictionary data first (idempotent - safe even if demo data exists)
        _seed_dict_items(db)

        # ---- Idempotency check -------------------------------------------------
        existing = db.query(User).filter(User.email == DEMO_ADMIN_EMAIL).first()
        if existing:
            print(f"Demo data already exists ({DEMO_ADMIN_EMAIL} found). Skipping.")
            return

        now = datetime.now(timezone.utc)
        today = date.today()

        # ---- Users -------------------------------------------------------------
        users = [
            User(
                name="Demo Admin",
                email="demo.admin@crm.com",
                phone="13900000001",
                password_hash=get_password_hash(DEMO_PASSWORD),
                role="admin",
                is_active=True,
            ),
            User(
                name="Zhang Wei",
                email="zhangwei@crm.com",
                phone="13900000002",
                password_hash=get_password_hash(DEMO_PASSWORD),
                role="sales",
                is_active=True,
            ),
            User(
                name="Li Na",
                email="lina@crm.com",
                phone="13900000003",
                password_hash=get_password_hash(DEMO_PASSWORD),
                role="sales",
                is_active=True,
            ),
            User(
                name="Wang Fang",
                email="wangfang@crm.com",
                phone="13900000004",
                password_hash=get_password_hash(DEMO_PASSWORD),
                role="sales",
                is_active=True,
            ),
            User(
                name="Chen Jie",
                email="chenjie@crm.com",
                phone="13900000005",
                password_hash=get_password_hash(DEMO_PASSWORD),
                role="pm",
                is_active=True,
            ),
            User(
                name="Liu Yang",
                email="liuyang@crm.com",
                phone="13900000006",
                password_hash=get_password_hash(DEMO_PASSWORD),
                role="cs",
                is_active=True,
            ),
        ]
        db.add_all(users)
        db.flush()

        admin_user = next(u for u in users if u.role == "admin")
        sales_users = [u for u in users if u.role == "sales"]
        pm_user = next(u for u in users if u.role == "pm")
        cs_user = next(u for u in users if u.role == "cs")

        # ---- Customers ---------------------------------------------------------
        customers: list[Customer] = []
        stage_list = _build_stage_list()
        phone_index = 1
        for (company, contact), stage in zip(CUSTOMER_DATA, stage_list):
            phone = f"138{phone_index:08d}"
            amount = 0 if stage < 3 else random.choice(CONTRACT_AMOUNTS)
            if stage >= 7:
                paid_amount = float(amount)
            elif stage == 6:
                paid_amount = random.choice(
                    [round(0.5 * amount, 2), round(0.8 * amount, 2), round(0.9 * amount, 2)]
                )
            elif stage == 5:
                paid_amount = random.choice(
                    [round(0.3 * amount, 2), round(0.5 * amount, 2), round(0.8 * amount, 2)]
                )
            elif stage == 4:
                paid_amount = random.choice([0, round(0.3 * amount, 2)])
            else:
                paid_amount = 0

            customers.append(
                Customer(
                    name=company,
                    contact_person=contact,
                    phone=phone,
                    wechat=f"wx_{phone}",
                    email=f"{contact.lower().replace(' ', '.')}@example.com",
                    company=company,
                    region=random.choice(REGIONS),
                    source_channel=random.choice(SOURCE_CHANNELS),
                    sales_id=random.choice(sales_users).id,
                    current_stage=stage,
                    stage_entered_at=now - timedelta(days=random.randint(*STAGE_STAY_RANGES[stage])),
                    contract_amount=amount,
                    paid_amount=paid_amount,
                    status="active",
                )
            )
            phone_index += 1

        db.add_all(customers)
        db.flush()

        # ---- Contracts (stage >= 3) --------------------------------------------
        contracts: list[Contract] = []
        contract_by_customer: dict = {}
        contract_index = 1
        for customer in customers:
            if customer.current_stage < 3:
                continue
            sign_date = customer.stage_entered_at.date() - timedelta(days=random.randint(1, 5))
            contract = Contract(
                customer_id=customer.id,
                contract_no=f"HT-2026-{contract_index:03d}",
                contract_amount=customer.contract_amount,
                sign_date=sign_date,
                payment_terms=random.choice(PAYMENT_TERMS_LIST),
                delivery_date=sign_date + timedelta(days=random.randint(30, 90)),
                contract_file=None,
            )
            contract_index += 1
            contracts.append(contract)
            contract_by_customer[customer.id] = contract

        # ---- Tasks (stage >= 4) -------------------------------------------------
        tasks: list[Task] = []
        for customer in customers:
            if customer.current_stage < 4:
                continue
            count = random.randint(2, 5)
            names = random.sample(TASK_NAMES, min(count, len(TASK_NAMES)))
            all_completed = customer.current_stage >= 5  # stages 5+ require all tasks done
            statuses = [random.choice(["pending", "in_progress", "completed"]) for _ in names]
            if all_completed:
                statuses = ["completed"] * len(names)
            elif all(s == "completed" for s in statuses):
                statuses[0] = random.choice(["pending", "in_progress"])

            for name, status in zip(names, statuses):
                assignee = (
                    pm_user if random.random() < 0.4 else next(u for u in sales_users if u.id == customer.sales_id)
                )
                if status == "completed":
                    start_date = today - timedelta(days=random.randint(20, 60))
                    due_date = start_date + timedelta(days=random.randint(5, 20))
                    completed_at = datetime(
                        due_date.year, due_date.month, due_date.day,
                        random.randint(9, 18), 0, 0, tzinfo=timezone.utc,
                    )
                else:
                    start_date = today - timedelta(days=random.randint(1, 10))
                    due_date = today + timedelta(days=random.randint(2, 10))
                    completed_at = None
                tasks.append(
                    Task(
                        customer_id=customer.id,
                        name=name,
                        description=f"{customer.name} 的 {name} 相关任务",
                        assignee_id=assignee.id,
                        status=status,
                        priority=random.choice(TASK_PRIORITIES),
                        start_date=start_date,
                        due_date=due_date,
                        completed_at=completed_at,
                    )
                )

        # ---- Communications (stage >= 2) ----------------------------------------
        communications: list[Communication] = []
        for customer in customers:
            if customer.current_stage < 2:
                continue
            for _ in range(random.randint(2, 5)):
                channel = random.choice(COMM_CHANNELS)
                communications.append(
                    Communication(
                        customer_id=customer.id,
                        user_id=customer.sales_id,
                        channel=channel,
                        content=COMM_CONTENTS[channel],
                        next_action=random.choice(COMM_NEXT_ACTIONS),
                        next_action_date=today + timedelta(days=random.randint(1, 15)),
                    )
                )

        # ---- Payments (stage >= 7) ----------------------------------------------
        payments: list[Payment] = []
        invoice_index = 1
        for customer in customers:
            if customer.current_stage < 7:
                continue
            amount = float(customer.contract_amount)
            contract = contract_by_customer.get(customer.id)
            sign_date = contract.sign_date if contract else customer.stage_entered_at.date() - timedelta(days=7)
            plan = random.choice(["two", "three"])
            if plan == "three":
                deposit = round(amount * 0.3, 2)
                milestone = round(amount * 0.4, 2)
                final = round(amount - deposit - milestone, 2)
                pay_plan = [
                    ("deposit", deposit, sign_date + timedelta(days=3)),
                    ("milestone", milestone, sign_date + timedelta(days=30)),
                    ("final", final, sign_date + timedelta(days=60)),
                ]
            else:
                deposit = round(amount * 0.3, 2)
                final = round(amount - deposit, 2)
                pay_plan = [
                    ("deposit", deposit, sign_date + timedelta(days=3)),
                    ("final", final, sign_date + timedelta(days=45)),
                ]
            for payment_type, pay_amount, pay_date in pay_plan:
                if pay_date > today:
                    pay_date = today
                payments.append(
                    Payment(
                        customer_id=customer.id,
                        amount=pay_amount,
                        payment_date=pay_date,
                        payment_type=payment_type,
                        invoice_no=f"INV-2026-{invoice_index:04d}",
                        notes={
                            "deposit": "Deposit payment",
                            "milestone": "Milestone payment",
                            "final": "Final payment",
                        }[payment_type],
                        recorded_by=random.choice([admin_user, *sales_users]).id,
                    )
                )
                invoice_index += 1

        # ---- Stage history (stage >= 2) ------------------------------------------
        histories: list[StageHistory] = []
        for customer in customers:
            for s in range(1, customer.current_stage):
                histories.append(
                    StageHistory(
                        customer_id=customer.id,
                        from_stage=s,
                        to_stage=s + 1,
                        changed_by=random.choice([admin_user, *sales_users]).id,
                        changed_at=customer.stage_entered_at - timedelta(days=random.randint(1, 15)),
                        remark=f"Advanced to stage {s + 1}",
                    )
                )

        db.add_all(contracts + communications + tasks + payments + histories)
        db.flush()

        # ---- Follow-ups (2-3, for sales users) -----------------------------------
        follow_ups: list[FollowUp] = []
        for sales in sales_users:
            owned = [c for c in customers if c.sales_id == sales.id]
            if not owned:
                continue
            customer = random.choice(owned)
            is_done = random.choice([True, False])
            follow_ups.append(
                FollowUp(
                    customer_id=customer.id,
                    user_id=sales.id,
                    title=f"回访跟进 - {customer.name}",
                    content="电话回访客户，确认项目进展并收集反馈意见。",
                    remind_at=now + timedelta(days=random.randint(1, 7)),
                    remind_type="system_notification",
                    is_done=is_done,
                    done_at=now - timedelta(days=random.randint(1, 3)) if is_done else None,
                )
            )

        # ---- Notifications (3-5) ---------------------------------------------------
        sample_task = tasks[0] if tasks else None
        sample_customer = customers[0]
        sample_follow_up = follow_ups[0] if follow_ups else None
        notifications = [
            Notification(
                user_id=pm_user.id,
                type="task",
                title="新任务待处理",
                content="有一个新的客户任务等待处理，请及时安排。",
                related_id=sample_task.id if sample_task else None,
                related_type="task",
                is_read=False,
            ),
            Notification(
                user_id=sales_users[0].id,
                type="stage_alert",
                title="客户阶段预警",
                content="部分客户在当前阶段停留时间较长，请及时跟进处理。",
                related_id=sample_customer.id,
                related_type="customer",
                is_read=False,
            ),
            Notification(
                user_id=cs_user.id,
                type="follow_up",
                title="跟进提醒",
                content="今天有待完成的客户跟进事项，请及时处理。",
                related_id=sample_follow_up.id if sample_follow_up else None,
                related_type="follow_up",
                is_read=False,
            ),
            Notification(
                user_id=admin_user.id,
                type="system",
                title="欢迎使用CRM系统",
                content="演示数据已就绪，可以开始体验各业务模块。",
                related_id=None,
                related_type=None,
                is_read=True,
            ),
        ]
        db.add_all(follow_ups + notifications)
        db.commit()

        # ---- Summary ---------------------------------------------------------------
        print("=" * 60)
        print("Demo data seeded successfully!")
        print(f"  Users:          {len(users)}")
        print(f"  Customers:      {len(customers)}")
        print(f"  Contracts:      {len(contracts)}")
        print(f"  Tasks:          {len(tasks)}")
        print(f"  Communications: {len(communications)}")
        print(f"  Payments:       {len(payments)}")
        print(f"  Stage history:  {len(histories)}")
        print(f"  Follow-ups:     {len(follow_ups)}")
        print(f"  Notifications:  {len(notifications)}")
        print()
        print("Demo credentials (password: demo123456):")
        print("  Admin: demo.admin@crm.com")
        print("  Sales: zhangwei@crm.com / lina@crm.com / wangfang@crm.com")
        print("  PM:    chenjie@crm.com")
        print("  CS:    liuyang@crm.com")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"Demo seeding failed, changes rolled back: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
