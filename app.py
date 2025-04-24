import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import tempfile

st.set_page_config(page_title="PLUS ONE", layout="wide")
st.title("📚 PLOS ONE 期刊作者與機構擷取工具")

doi_input = st.text_area("請輸入 DOI（每行一筆, 限PLOS ONE期刊之論文）")
run_button = st.button("🚀 開始擷取")

if run_button and doi_input.strip():
    dois = [d.strip() for d in doi_input.strip().split("\n")]
    all_records = []
    seen_names = set()  # 用來記錄已經出現過的作者姓名，避免重複

    for doi in dois:
        xml_url = f"https://journals.plos.org/plosone/article/file?id={doi}&type=manuscript"
        response = requests.get(xml_url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "lxml-xml")

            # 文章標題
            article_title = soup.find("article-title")
            title = article_title.get_text(strip=True) if article_title else "N/A"

            # 建立 aff 對應表
            aff_dict = {
                aff.get("id"): aff.find("addr-line").get_text(strip=True) if aff.find("addr-line") else aff.get_text(strip=True)
                for aff in soup.find_all("aff")
            }

            # 🔍 只在 <front> 的 <contrib-group> 裡抓作者，避免抓到附錄或參與名單
            author_group = soup.find("contrib-group")
            authors = author_group.find_all("contrib", {"contrib-type": "author"}) if author_group else []


            for idx, author in enumerate(authors, start=1):
                surname = author.find("surname")
                given_names = author.find("given-names")
                name = f"{given_names.text.strip()} {surname.text.strip()}" if given_names and surname else surname.text.strip() if surname else "N/A"

             # 避免重複作者名
                if name in seen_names:
                    continue
                seen_names.add(name)

                # 標記第一作者 / 通訊作者
                if idx == 1:
                   name += "（第一作者）"
                elif author.find("xref", {"ref-type": "corresp"}):
                   name += "（通訊作者）"

                # 找對應機構
                aff_ref = author.find("xref", {"ref-type": "aff"})
                aff_id = aff_ref.get("rid") if aff_ref else None
                affiliation = aff_dict.get(aff_id, "N/A")

                # 儲存資料
                all_records.append({
                    "Order": idx,
                    "Title": title,
                    "Name": name,
                    "Affiliation": affiliation,
                    "DOI": doi
                })

        else:
            st.warning(f"❌ 無法取得 DOI: {doi}")

    df = pd.DataFrame(all_records)

    if df.empty:
        st.warning("⚠️ 沒有擷取到任何作者資訊，請檢查 DOI 是否正確。")
    else:
        st.success("✅ 擷取成功！")

        # 重新設定索引，從 1 開始
        df.index = range(1, len(df) + 1)

        # 顯示表格
        st.dataframe(df, use_container_width=True)

        # 提供 Excel 下載
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            df.to_excel(tmp.name, index=True)
            st.download_button("📥 下載 Excel", data=open(tmp.name, 'rb'), file_name="authors_affiliations.xlsx")
