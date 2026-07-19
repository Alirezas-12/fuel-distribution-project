import streamlit as st
import pandas as pd
from groq import Groq
from fuel_lp_module import FuelDistributionLP
from fuel_ga_module import FuelDistributionGA

st.set_page_config(page_title="سیستم پخش فرآورده‌های نفتی", layout="wide")
st.title("سیستم پخش فرآورده‌های نفتی و جایگاه‌های سوخت")

tab1, tab2, tab3 = st.tabs(
    ["ماژول LP - ارسال به انبار", "ماژول GA - زمان‌بندی توزیع", "چت‌بات تحلیلی"]
)

# ---------------- تب ۱: ماژول LP ----------------
with tab1:
    st.subheader("ظرفیت عرضه پالایشگاه‌ها")
    supply_df = st.data_editor(
        pd.DataFrame({"پالایشگاه": ["R1", "R2"], "ظرفیت عرضه": [1000, 800]}),
        num_rows="dynamic", key="supply_editor",
    )

    st.subheader("تقاضای انبارهای استانی")
    demand_df = st.data_editor(
        pd.DataFrame({"انبار": ["D1", "D2", "D3"], "تقاضا": [500, 600, 400]}),
        num_rows="dynamic", key="demand_editor",
    )

    st.subheader("مسیرها (هزینه و ظرفیت هر مسیر)")
    routes_df = st.data_editor(
        pd.DataFrame({
            "پالایشگاه": ["R1", "R1", "R1", "R2", "R2", "R2"],
            "انبار": ["D1", "D2", "D3", "D1", "D2", "D3"],
            "حالت حمل": ["pipeline", "pipeline", "rail", "rail", "pipeline", "pipeline"],
            "هزینه واحد": [2, 3, 5, 4, 2, 3],
            "ظرفیت مسیر": [700, 700, 700, 700, 700, 700],
        }),
        num_rows="dynamic", key="routes_editor",
    )

    if st.button("حل مسئله LP", key="run_lp"):
        refineries = supply_df["پالایشگاه"].tolist()
        depots = demand_df["انبار"].tolist()

        lp = FuelDistributionLP(refineries=refineries, depots=depots)
        lp.set_supply(dict(zip(supply_df["پالایشگاه"], supply_df["ظرفیت عرضه"])))
        lp.set_demand(dict(zip(demand_df["انبار"], demand_df["تقاضا"])))

        cost_dict, cap_dict = {}, {}
        for _, row in routes_df.iterrows():
            key = (row["پالایشگاه"], row["انبار"], row["حالت حمل"])
            cost_dict[key] = row["هزینه واحد"]
            cap_dict[key] = row["ظرفیت مسیر"]
        lp.set_cost(cost_dict)
        lp.set_capacity(cap_dict)

        lp.build_model()
        result = lp.solve()

        if result["status"] == "Optimal":
            st.session_state["lp_result"] = result
            st.success(f"وضعیت: {result['status']} | هزینه کل بهینه: {result['objective']}")

            ship_df = pd.DataFrame([
                {"مسیر": f"{i} -> {j} ({m})", "مقدار": v}
                for (i, j, m), v in result["shipments"].items()
            ])
            st.dataframe(ship_df, use_container_width=True)
            st.bar_chart(ship_df.set_index("مسیر"))

            st.subheader("ارزش‌های سایه‌ای (تحلیل حساسیت)")
            shadow_df = pd.DataFrame([
                {"قید": name, "ارزش سایه‌ای": v}
                for name, v in result["shadow_prices"].items()
            ])
            st.dataframe(shadow_df, use_container_width=True)
        else:
            st.error(f"وضعیت حل: {result['status']} — مسئله شدنی نیست، پارامترها رو چک کن")

# ---------------- تب ۲: ماژول GA ----------------
with tab2:
    st.subheader("جایگاه‌های سوخت")
    stations_df = st.data_editor(
        pd.DataFrame({
            "جایگاه": ["S0", "S1", "S2", "S3", "S4"],
            "حجم (q)": [500, 300, 400, 600, 200],
            "زمان سرویس (p)": [30, 20, 25, 35, 15],
            "ددلاین (d)": [120, 90, 150, 100, 200],
            "زمان آماده (r)": [0, 0, 0, 0, 0],
        }),
        num_rows="dynamic", key="stations_editor",
    )

    col1, col2 = st.columns(2)
    with col1:
        num_tankers = st.number_input("تعداد تانکر", min_value=1, value=2, step=1)
    with col2:
        tanker_capacity = st.number_input("ظرفیت هر تانکر", min_value=1, value=1200, step=50)

    if st.button("اجرای الگوریتم ژنتیک", key="run_ga"):
        renamed = stations_df.rename(columns={
            "حجم (q)": "q", "زمان سرویس (p)": "p", "ددلاین (d)": "d", "زمان آماده (r)": "r",
        })
        stations = renamed.to_dict("records")

        ga = FuelDistributionGA(
            stations=stations, num_tankers=int(num_tankers), tanker_capacity=tanker_capacity
        )
        best_chromo, best_fit = ga.run()

        schedule = ga.get_schedule(best_chromo)
        result_df = pd.DataFrame(schedule)
        result_df["جایگاه"] = result_df["station_index"].apply(
            lambda idx: stations_df.iloc[idx]["جایگاه"]
        )
        result_df = result_df[["tanker", "جایگاه", "start", "finish", "deadline", "tardiness"]]
        result_df.columns = ["تانکر", "جایگاه", "شروع", "پایان", "ددلاین", "دیرکرد"]

        st.session_state["ga_result"] = {
            "بهترین_دیرکرد_کل": best_fit,
            "جدول_زمان‌بندی": result_df.to_dict("records"),
        }
        st.success(f"بهترین مجموع دیرکرد: {best_fit}")
        st.dataframe(result_df, use_container_width=True)
        st.bar_chart(result_df.set_index("جایگاه")["دیرکرد"])

# ---------------- تب ۳: چت‌بات تحلیلی ----------------
with tab3:
    st.subheader("از نتایج بپرس")

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_question = st.chat_input("مثلاً: چرا این مسیر انتخاب شد؟ یا: اگه تقاضای D2 بیشتر بشه چی میشه؟")

    if user_question:
        st.session_state["chat_history"].append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.write(user_question)

        context_parts = []
        if "lp_result" in st.session_state:
            context_parts.append(f"نتیجه ماژول LP: {st.session_state['lp_result']}")
        if "ga_result" in st.session_state:
            context_parts.append(f"نتیجه ماژول GA: {st.session_state['ga_result']}")
        if not context_parts:
            context_parts.append("هنوز هیچ مسئله‌ای (نه LP و نه GA) حل نشده.")
        context = "\n".join(context_parts)

        system_prompt = (
            "تو دستیار تحلیلی یک سیستم بهینه‌سازی پخش فرآورده‌های نفتی هستی. "
            "بر اساس داده‌های زیر که از حل واقعی مسئله به‌دست اومده، کوتاه و دقیق "
            "به سوال کاربر درباره پارامترها، دلیل بهینگی، تحلیل حساسیت یا پیشنهاد مدیریتی جواب بده:\n"
            f"{context}"
        )

        with st.chat_message("assistant"):
            with st.spinner("در حال فکر کردن..."):
                try:
                    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
                    response = client.chat.completions.create(
                        model="openai/gpt-oss-120b",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_question},
                        ],
                    )
                    answer = response.choices[0].message.content
                except Exception as e:
                    answer = f"خطا در اتصال به چت‌بات: {e}"
                st.write(answer)

        st.session_state["chat_history"].append({"role": "assistant", "content": answer})
