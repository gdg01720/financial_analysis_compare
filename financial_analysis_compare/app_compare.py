import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import os
import io

# --- 1. 日本語フォント設定 (ローカル & Cloud 両対応) ---
def setup_font():
    """fontsフォルダからフォントを読み込み、日本語表示を有効化"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(current_dir, "fonts", "ipaexg.ttf")
    if os.path.exists(font_path):
        fm.fontManager.addfont(font_path)
        prop = fm.FontProperties(fname=font_path)
        plt.rcParams['font.family'] = prop.get_name()
        return prop.get_name()
    else:
        # フォールバック: システムフォントを試行
        plt.rcParams['font.family'] = ['Meiryo', 'MS Gothic', 'Hiragino Sans', 'sans-serif']
        return 'sans-serif'

font_name = setup_font()
sns.set_theme(style="whitegrid", rc={"font.family": font_name})

st.set_page_config(
    page_title="企業財務比較ダッシュボード", 
    layout="wide",
    page_icon="📊"
)

# --- 2. カラーパレット定義 ---
COLORS = {
    'primary': ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#3B1F2B', '#95C623', '#5C4D7D'],
    'accent': '#FF6B6B',
    'background': '#F8F9FA',
    'text': '#2C3E50'
}

def get_company_colors(companies):
    """企業ごとに一貫した色を割り当て"""
    return {company: COLORS['primary'][i % len(COLORS['primary'])] for i, company in enumerate(companies)}

# --- 3. ユーティリティ関数 ---
def format_fy(year):
    """年度をFYフォーマットに変換"""
    try:
        return f"FY{int(year)}"
    except:
        return year

def convert_to_million(df):
    """10万以上の数値を百万円単位に変換"""
    df = df.copy()
    numeric_columns = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
    for column in numeric_columns:
        df[column] = df[column].apply(lambda x: (x / 1000000.0) if pd.notna(x) and np.abs(x) >= 100000 else x)
    return df

def safe_divide(numerator, denominator, default=0):
    """ゼロ除算を回避する除算"""
    return np.where(denominator != 0, numerator / denominator, default)

def get_html_report(df, title, fig=None):
    """HTMLダウンロード用データの生成（テーブル＋チャート）"""
    import base64
    from io import BytesIO
    
    # チャートをbase64エンコード
    chart_html = ""
    if fig is not None:
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        chart_html = f'<div style="text-align:center; margin: 20px 0;"><img src="data:image/png;base64,{img_base64}" style="max-width:100%;"/></div>'
    
    return f"""
    <html><head><meta charset='utf-8'>
    <style>
        body {{ font-family: 'Hiragino Sans', 'Meiryo', sans-serif; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; background: white; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: right; }}
        th {{ background: linear-gradient(135deg, #2E86AB, #A23B72); color: white; text-align: center; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        tr:hover {{ background-color: #f0f0f0; }}
        h2 {{ color: #2C3E50; border-left: 5px solid #2E86AB; padding-left: 15px; margin-top: 0; }}
        .timestamp {{ color: #888; font-size: 12px; text-align: right; margin-top: 20px; }}
    </style></head>
    <body>
    <div class="container">
        <h2>{title}</h2>
        {chart_html}
        <h3>📋 詳細データ</h3>
        {df.to_html(classes='data-table')}
        <p class="timestamp">生成日時: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    </body></html>
    """

# --- 4. データの読み込み ---
@st.cache_data
def load_financial_data():
    """財務データの読み込みと前処理"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_dir, "data", "financial_data.xlsx")
    
    if os.path.exists(path):
        df = pd.read_excel(path)
        # 欠損値（ハイフン）を0に置換
        num_cols = df.columns.drop(['企業名', '決算年度', '決算四半期'], errors='ignore')
        for col in num_cols:
            df[col] = pd.to_numeric(df[col].astype(str).replace('-', '0').replace('', '0'), errors='coerce').fillna(0)
        
        # 単位変換処理を適用
        df = convert_to_million(df)
        return df
    return None

# --- 5. 企業名マッピング定義（表示名→データ名） ---
# 一部の企業名はUIでの表示名と実際のデータでの名前が異なるため、マッピングを定義
COMPANY_NAME_MAPPING = {
    'フジ・リテイリング': 'フジ',
    'U.S.M.H': 'USMH',
    'マックスバリュ東海': 'マックスバリュー東海',
}

# 逆マッピング（データ名→表示名）
COMPANY_NAME_REVERSE_MAPPING = {v: k for k, v in COMPANY_NAME_MAPPING.items()}

def get_data_name(display_name):
    """表示名からデータ名に変換"""
    return COMPANY_NAME_MAPPING.get(display_name, display_name)

def get_display_name(data_name):
    """データ名から表示名に変換"""
    return COMPANY_NAME_REVERSE_MAPPING.get(data_name, data_name)

def get_data_names(display_names):
    """表示名リストからデータ名リストに変換"""
    return [get_data_name(name) for name in display_names]

def get_display_names(data_names):
    """データ名リストから表示名リストに変換"""
    return [get_display_name(name) for name in data_names]

# --- 6. 業種グループ定義（表示名で定義） ---
INDUSTRY_GROUPS = {
    'イオングループ': ['イオン北海道', 'イオン九州', 'マックスバリュ東海', 'フジ・リテイリング', 'U.S.M.H', 'ツルハ'],
    'ドラッグストア': ['ツルハ', 'マツキヨココカラ', 'コスモス薬品', 'クリエイトSD', 'サンドラッグ', 'スギ薬局', 'クスリのアオキ'],
    'ホームセンター': ['DCMHD', 'コーナン', 'コメリ', 'アークランズ', 'ジョイフル本田'],
    'スーパーマーケット（全国）': ['PPIH', 'トライアル'],
    'スーパーマーケット（東日本）': ['イオン北海道', 'アークス', 'ヤオコー', 'ライフ', 'ベルク', 'U.S.M.H'],
    'スーパーマーケット（西日本）': ['平和堂', 'バロー', 'イズミ', 'ライフ', 'ハローズ', 'マックスバリュ東海', 'フジ・リテイリング'],
    'カスタム': []  # ユーザーが自由に選択
}

# --- 7. メイン UI ---
st.title("📊 企業財務比較ダッシュボード")
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #f0f2f6; 
        border-radius: 8px 8px 0 0; 
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #2E86AB; 
        color: white;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

df_raw = load_financial_data()

if df_raw is not None:
    # --- サイドバー設定 ---
    st.sidebar.header("🔧 分析条件")
    
    # 利用可能な企業リスト（データ名）
    available_data_names = sorted(df_raw['企業名'].unique().tolist())
    # 表示用の企業リスト（表示名に変換）
    available_display_names = sorted([get_display_name(c) for c in available_data_names])
    
    # 業種グループ選択
    industry_choice = st.sidebar.selectbox(
        "業種グループを選択",
        list(INDUSTRY_GROUPS.keys())
    )
    
    # 企業選択
    if industry_choice == 'カスタム':
        default_display_names = available_display_names[:5]
        selected_display_names = st.sidebar.multiselect(
            "比較企業を選択（最大7社）",
            available_display_names,
            default=default_display_names,
            max_selections=7
        )
    else:
        # INDUSTRY_GROUPSの表示名をデータ名に変換してから、利用可能な企業と照合
        preset_display_names = INDUSTRY_GROUPS[industry_choice]
        # 利用可能な企業のみフィルタリング（データ名で照合）
        valid_display_names = [
            name for name in preset_display_names 
            if get_data_name(name) in available_data_names
        ]
        selected_display_names = st.sidebar.multiselect(
            "比較企業を選択（最大7社）",
            available_display_names,
            default=valid_display_names[:7],
            max_selections=7
        )
    
    # 選択された表示名をデータ名に変換
    selected_companies = get_data_names(selected_display_names)
    
    # 比較年度選択
    available_years = df_raw['決算年度'].dropna().unique().tolist()
    # 数値型に変換（numpy型からPython intへ）、NaN除外
    available_years = sorted([int(y) for y in available_years if pd.notna(y)], reverse=True)
    selected_year = st.sidebar.selectbox(
        "比較年度を選択",
        available_years,
        format_func=format_fy
    )
    
    # 時系列比較オプション
    show_trend = st.sidebar.checkbox("過去5年トレンドを表示", value=False)
    
    if not selected_companies:
        st.warning("⚠️ 比較する企業を1社以上選択してください。")
    else:
        # データフィルタリング
        mask = (df_raw['企業名'].isin(selected_companies)) & (df_raw['決算年度'] == selected_year)
        df_compare = df_raw[mask].copy()
        
        # トレンドデータ
        if show_trend:
            start_year = selected_year - 4
            trend_mask = (df_raw['企業名'].isin(selected_companies)) & \
                        (df_raw['決算年度'] >= start_year) & \
                        (df_raw['決算年度'] <= selected_year)
            df_trend = df_raw[trend_mask].copy()
        
        company_colors = get_company_colors(selected_companies)
        
        if df_compare.empty:
            st.warning("選択された条件に該当するデータがありません。")
        else:
            # 表示名の列を追加
            df_compare['企業名_表示'] = df_compare['企業名'].apply(get_display_name)
            
            # --- サマリーカード ---
            st.subheader(f"📈 {format_fy(selected_year)} 主要指標サマリー")
            cols = st.columns(len(selected_companies))
            for i, company in enumerate(selected_companies):
                company_data = df_compare[df_compare['企業名'] == company]
                if not company_data.empty:
                    row = company_data.iloc[0]
                    display_name = get_display_name(company)
                    with cols[i]:
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, {company_colors[company]}, {company_colors[company]}99); 
                                    padding: 15px; border-radius: 10px; color: white; text-align: center;">
                            <h4 style="margin:0; font-size:14px;">{display_name}</h4>
                            <p style="margin:5px 0; font-size:12px;">売上高: {row['売上高']:,.0f}百万円</p>
                            <p style="margin:5px 0; font-size:12px;">営業利益率: {row['営業利益率']:.1f}%</p>
                        </div>
                        """, unsafe_allow_html=True)
            
            st.divider()
            
            # --- タブ構成 ---
            tab_pl, tab_structure, tab_bs, tab_cf, tab_prod = st.tabs([
                "📊 収益比較(PL)", "🏗️ 収益・コスト構造", "🏦 財政状態(BS)", 
                "💰 キャッシュフロー", "👥 労働生産性"
            ])
            
            # ========== タブ1: 収益比較(PL) ==========
            with tab_pl:
                st.subheader("収益指標の企業間比較")
                
                # 計算: 成長率（2019年基準）
                df_growth = df_compare.copy()
                for company in selected_companies:
                    base_data = df_raw[(df_raw['企業名'] == company) & (df_raw['決算年度'] == selected_year - 5)]
                    if not base_data.empty:
                        base_sales = base_data['売上高'].values[0]
                        if base_sales > 0:
                            current_sales = df_growth[df_growth['企業名'] == company]['売上高'].values
                            if len(current_sales) > 0:
                                df_growth.loc[df_growth['企業名'] == company, '売上高成長率'] = current_sales[0] / base_sales
                        else:
                            df_growth.loc[df_growth['企業名'] == company, '売上高成長率'] = 1.0
                    else:
                        df_growth.loc[df_growth['企業名'] == company, '売上高成長率'] = 1.0
                
                fig, axs = plt.subplots(2, 2, figsize=(14, 10))
                
                companies_data = df_compare['企業名'].tolist()
                companies = df_compare['企業名_表示'].tolist()  # 表示名
                colors = [company_colors[c] for c in companies_data]
                
                # 売上高
                axs[0, 0].bar(companies, df_compare['売上高'], color=colors)
                axs[0, 0].set_title('売上高（百万円）', fontsize=12, fontweight='bold')
                axs[0, 0].tick_params(axis='x', rotation=45)
                for i, v in enumerate(df_compare['売上高']):
                    axs[0, 0].text(i, v + v*0.02, f'{v:,.0f}', ha='center', fontsize=8)
                
                # 営業利益
                axs[0, 1].bar(companies, df_compare['営業利益'], color=colors)
                axs[0, 1].set_title('営業利益（百万円）', fontsize=12, fontweight='bold')
                axs[0, 1].tick_params(axis='x', rotation=45)
                for i, v in enumerate(df_compare['営業利益']):
                    axs[0, 1].text(i, v + v*0.02, f'{v:,.0f}', ha='center', fontsize=8)
                
                # 売上高成長率
                if '売上高成長率' in df_growth.columns:
                    growth_values = df_growth['売上高成長率'].fillna(1.0).tolist()
                    axs[1, 0].plot(companies, growth_values, marker='o', markersize=10, linewidth=2, color=COLORS['accent'])
                    axs[1, 0].axhline(y=1.0, color='gray', linestyle='--', alpha=0.5)
                    axs[1, 0].set_title(f'売上高成長率（{format_fy(selected_year-5)}=1.0）', fontsize=12, fontweight='bold')
                    axs[1, 0].tick_params(axis='x', rotation=45)
                    for i, v in enumerate(growth_values):
                        axs[1, 0].text(i, v + 0.02, f'{v:.2f}', ha='center', fontsize=9)
                
                # 営業利益率
                axs[1, 1].plot(companies, df_compare['営業利益率'].tolist(), marker='s', markersize=10, linewidth=2, color='#2E86AB')
                axs[1, 1].set_title('売上高営業利益率（%）', fontsize=12, fontweight='bold')
                axs[1, 1].tick_params(axis='x', rotation=45)
                for i, v in enumerate(df_compare['営業利益率']):
                    axs[1, 1].text(i, v + 0.1, f'{v:.1f}%', ha='center', fontsize=9)
                
                plt.tight_layout()
                st.pyplot(fig)
                
                # チャートを保存（HTMLダウンロード用）
                fig_pl = fig
                
                # データテーブル
                st.markdown("##### 📋 詳細データ")
                display_cols = ['企業名_表示', '売上高', '営業収入', '売上総利益率', '販管費', '営業利益', '営業利益率']
                display_df = df_compare[display_cols].copy()
                display_df = display_df.rename(columns={'企業名_表示': '企業名'}).set_index('企業名')
                st.dataframe(
                    display_df.style.format({
                        '売上高': '{:,.0f}', '営業収入': '{:,.0f}', '販管費': '{:,.0f}', 
                        '営業利益': '{:,.0f}', '売上総利益率': '{:.1f}', '営業利益率': '{:.1f}'
                    }).background_gradient(cmap='Blues', subset=['営業利益率']),
                    use_container_width=True
                )
                
                html_content = get_html_report(display_df, f"収益比較 - {format_fy(selected_year)}", fig_pl)
                st.download_button("📥 HTMLでダウンロード（チャート＋テーブル）", html_content, "pl_comparison.html", "text/html")
                
                # ========== 主要KPI（PLタブ内） ==========
                st.divider()
                st.subheader("📈 主要KPI比較")
                
                companies_kpi = df_compare['企業名_表示'].tolist()  # 表示名
                
                # 安全にデータを取得する関数
                def safe_get_values(df, col_name, default=0):
                    if col_name in df.columns:
                        return df[col_name].fillna(default).tolist()
                    return [default] * len(df)
                
                # --- 収益性指標 ---
                st.markdown("##### 📊 収益性指標")
                
                # データ取得
                roic_values = safe_get_values(df_compare, 'ROIC', 0)
                roe_jissitsu_values = safe_get_values(df_compare, '実質ROE', 0)
                roa_values = safe_get_values(df_compare, 'ROA', 0)
                roe_values = safe_get_values(df_compare, 'ROE', 0)
                
                fig_kpi, axs_kpi = plt.subplots(2, 2, figsize=(14, 10))
                
                # ROIC
                axs_kpi[0, 0].plot(companies_kpi, roic_values, marker='o', markersize=12, linewidth=2, color='#2E86AB')
                axs_kpi[0, 0].set_title('ROIC（%）', fontsize=12, fontweight='bold')
                axs_kpi[0, 0].tick_params(axis='x', rotation=45)
                mean_roic = np.mean([v for v in roic_values if v != 0]) if any(v != 0 for v in roic_values) else 0
                if mean_roic != 0:
                    axs_kpi[0, 0].axhline(y=mean_roic, color='gray', linestyle='--', alpha=0.5)
                for i, v in enumerate(roic_values):
                    if v != 0:
                        axs_kpi[0, 0].text(i, v + 0.3, f'{v:.1f}%', ha='center', fontsize=9)
                
                # 実質ROE
                axs_kpi[0, 1].plot(companies_kpi, roe_jissitsu_values, marker='s', markersize=12, linewidth=2, color='#A23B72')
                axs_kpi[0, 1].set_title('実質ROE（%）', fontsize=12, fontweight='bold')
                axs_kpi[0, 1].tick_params(axis='x', rotation=45)
                mean_roe_j = np.mean([v for v in roe_jissitsu_values if v != 0]) if any(v != 0 for v in roe_jissitsu_values) else 0
                if mean_roe_j != 0:
                    axs_kpi[0, 1].axhline(y=mean_roe_j, color='gray', linestyle='--', alpha=0.5)
                for i, v in enumerate(roe_jissitsu_values):
                    if v != 0:
                        axs_kpi[0, 1].text(i, v + 0.3, f'{v:.1f}%', ha='center', fontsize=9)
                
                # ROA
                axs_kpi[1, 0].plot(companies_kpi, roa_values, marker='^', markersize=12, linewidth=2, color='#95C623')
                axs_kpi[1, 0].set_title('ROA（%）', fontsize=12, fontweight='bold')
                axs_kpi[1, 0].tick_params(axis='x', rotation=45)
                mean_roa = np.mean([v for v in roa_values if v != 0]) if any(v != 0 for v in roa_values) else 0
                if mean_roa != 0:
                    axs_kpi[1, 0].axhline(y=mean_roa, color='gray', linestyle='--', alpha=0.5)
                for i, v in enumerate(roa_values):
                    if v != 0:
                        axs_kpi[1, 0].text(i, v + 0.2, f'{v:.1f}%', ha='center', fontsize=9)
                
                # ROE
                axs_kpi[1, 1].plot(companies_kpi, roe_values, marker='D', markersize=12, linewidth=2, color='#F18F01')
                axs_kpi[1, 1].set_title('ROE（%）', fontsize=12, fontweight='bold')
                axs_kpi[1, 1].tick_params(axis='x', rotation=45)
                mean_roe = np.mean([v for v in roe_values if v != 0]) if any(v != 0 for v in roe_values) else 0
                if mean_roe != 0:
                    axs_kpi[1, 1].axhline(y=mean_roe, color='gray', linestyle='--', alpha=0.5)
                for i, v in enumerate(roe_values):
                    if v != 0:
                        axs_kpi[1, 1].text(i, v + 0.2, f'{v:.1f}%', ha='center', fontsize=9)
                
                plt.tight_layout()
                st.pyplot(fig_kpi)
                
                st.divider()
                
                # --- 株価指標 ---
                st.markdown("##### 📈 株価指標・時価総額")
                
                # データ取得
                per_values = safe_get_values(df_compare, 'PER（会予）', 0)
                pbr_values = safe_get_values(df_compare, 'PBR', 0)
                div_values = safe_get_values(df_compare, '配当利回り（実績）', 0)
                market_cap_values = safe_get_values(df_compare, '時価総額', 0)
                
                fig_kpi2, axs_kpi2 = plt.subplots(2, 2, figsize=(14, 10))
                
                # PER
                axs_kpi2[0, 0].bar(companies_kpi, per_values, color='#5C4D7D')
                axs_kpi2[0, 0].set_title('PER（会社予想）（倍）', fontsize=12, fontweight='bold')
                axs_kpi2[0, 0].tick_params(axis='x', rotation=45)
                mean_per = np.mean([v for v in per_values if v > 0]) if any(v > 0 for v in per_values) else 0
                if mean_per > 0:
                    axs_kpi2[0, 0].axhline(y=mean_per, color='gray', linestyle='--', alpha=0.5)
                for i, v in enumerate(per_values):
                    if v > 0:
                        axs_kpi2[0, 0].text(i, v + 0.5, f'{v:.1f}', ha='center', fontsize=9)
                
                # PBR
                axs_kpi2[0, 1].bar(companies_kpi, pbr_values, color='#C73E1D')
                axs_kpi2[0, 1].set_title('PBR（倍）', fontsize=12, fontweight='bold')
                axs_kpi2[0, 1].tick_params(axis='x', rotation=45)
                axs_kpi2[0, 1].axhline(y=1.0, color='red', linestyle='--', alpha=0.7, label='PBR=1.0')
                mean_pbr = np.mean([v for v in pbr_values if v > 0]) if any(v > 0 for v in pbr_values) else 0
                if mean_pbr > 0:
                    axs_kpi2[0, 1].axhline(y=mean_pbr, color='gray', linestyle='--', alpha=0.5)
                for i, v in enumerate(pbr_values):
                    if v > 0:
                        axs_kpi2[0, 1].text(i, v + 0.05, f'{v:.2f}', ha='center', fontsize=9)
                
                # 配当利回り
                axs_kpi2[1, 0].bar(companies_kpi, div_values, color='#95C623')
                axs_kpi2[1, 0].set_title('配当利回り（実績）（%）', fontsize=12, fontweight='bold')
                axs_kpi2[1, 0].tick_params(axis='x', rotation=45)
                mean_div = np.mean([v for v in div_values if v > 0]) if any(v > 0 for v in div_values) else 0
                if mean_div > 0:
                    axs_kpi2[1, 0].axhline(y=mean_div, color='gray', linestyle='--', alpha=0.5)
                for i, v in enumerate(div_values):
                    if v > 0:
                        axs_kpi2[1, 0].text(i, v + 0.05, f'{v:.2f}%', ha='center', fontsize=9)
                
                # 時価総額
                axs_kpi2[1, 1].bar(companies_kpi, market_cap_values, color='gold', edgecolor='#333')
                axs_kpi2[1, 1].set_title('時価総額（百万円）', fontsize=12, fontweight='bold')
                axs_kpi2[1, 1].tick_params(axis='x', rotation=45)
                for i, v in enumerate(market_cap_values):
                    if v > 0:
                        axs_kpi2[1, 1].text(i, v + v*0.02, f'{v:,.0f}', ha='center', fontsize=8)
                
                plt.tight_layout()
                st.pyplot(fig_kpi2)
                
                st.divider()
                
                # --- KPI総合評価テーブル ---
                st.markdown("##### 📋 KPI総合評価")
                
                # 収益性指標
                kpi_metrics = ['ROIC', '実質ROE', 'ROA', 'ROE', '営業利益率', '自己資本比率']
                available_kpi_metrics = [m for m in kpi_metrics if m in df_compare.columns]
                if available_kpi_metrics:
                    kpi_data = df_compare[['企業名_表示'] + available_kpi_metrics].copy()
                    kpi_data = kpi_data.rename(columns={'企業名_表示': '企業名'})
                    st.dataframe(
                        kpi_data.set_index('企業名').style.format('{:.1f}').background_gradient(cmap='RdYlGn'),
                        use_container_width=True
                    )
                
                # 株価指標テーブル
                st.markdown("##### 📋 株価指標詳細")
                stock_cols = ['企業名_表示', 'PER（会予）', 'PBR', '配当利回り（実績）', '時価総額']
                available_stock_cols = [c for c in stock_cols if c in df_compare.columns]
                if available_stock_cols:
                    stock_data = df_compare[available_stock_cols].copy()
                    stock_data = stock_data.rename(columns={'企業名_表示': '企業名'})
                    
                    format_dict_stock = {}
                    for col in stock_data.columns:
                        if col == '企業名':
                            continue
                        elif col == '時価総額':
                            format_dict_stock[col] = '{:,.0f}'
                        else:
                            format_dict_stock[col] = '{:.2f}'
                    
                    st.dataframe(
                        stock_data.set_index('企業名').style.format(format_dict_stock),
                        use_container_width=True
                    )
                
                # KPIダウンロードボタン
                kpi_cols = ['企業名_表示', 'ROE', '実質ROE', 'ROA', 'ROIC', '営業利益率', '自己資本比率', 'PER（会予）', 'PBR', '配当利回り（実績）', '時価総額']
                available_kpi_cols = [c for c in kpi_cols if c in df_compare.columns]
                kpi_display = df_compare[available_kpi_cols].copy()
                kpi_display = kpi_display.rename(columns={'企業名_表示': '企業名'}).set_index('企業名')
                
                # 統合チャートを作成してHTMLダウンロード用
                fig_combined, axs_combined = plt.subplots(2, 4, figsize=(20, 10))
                
                # Row 1: 収益性指標
                axs_combined[0, 0].plot(companies_kpi, roic_values, marker='o', markersize=10, linewidth=2, color='#2E86AB')
                axs_combined[0, 0].set_title('ROIC（%）'); axs_combined[0, 0].tick_params(axis='x', rotation=45)
                
                axs_combined[0, 1].plot(companies_kpi, roe_jissitsu_values, marker='s', markersize=10, linewidth=2, color='#A23B72')
                axs_combined[0, 1].set_title('実質ROE（%）'); axs_combined[0, 1].tick_params(axis='x', rotation=45)
                
                axs_combined[0, 2].plot(companies_kpi, roa_values, marker='^', markersize=10, linewidth=2, color='#95C623')
                axs_combined[0, 2].set_title('ROA（%）'); axs_combined[0, 2].tick_params(axis='x', rotation=45)
                
                axs_combined[0, 3].plot(companies_kpi, roe_values, marker='D', markersize=10, linewidth=2, color='#F18F01')
                axs_combined[0, 3].set_title('ROE（%）'); axs_combined[0, 3].tick_params(axis='x', rotation=45)
                
                # Row 2: 株価指標
                axs_combined[1, 0].bar(companies_kpi, per_values, color='#5C4D7D')
                axs_combined[1, 0].set_title('PER（倍）'); axs_combined[1, 0].tick_params(axis='x', rotation=45)
                
                axs_combined[1, 1].bar(companies_kpi, pbr_values, color='#C73E1D')
                axs_combined[1, 1].set_title('PBR（倍）'); axs_combined[1, 1].tick_params(axis='x', rotation=45)
                axs_combined[1, 1].axhline(y=1.0, color='red', linestyle='--', alpha=0.7)
                
                axs_combined[1, 2].bar(companies_kpi, div_values, color='#95C623')
                axs_combined[1, 2].set_title('配当利回り（%）'); axs_combined[1, 2].tick_params(axis='x', rotation=45)
                
                axs_combined[1, 3].bar(companies_kpi, market_cap_values, color='gold', edgecolor='#333')
                axs_combined[1, 3].set_title('時価総額（百万円）'); axs_combined[1, 3].tick_params(axis='x', rotation=45)
                
                plt.tight_layout()
                plt.close(fig_combined)
                
                html_content_kpi = get_html_report(kpi_display, f"主要KPI比較 - {format_fy(selected_year)}", fig_combined)
                st.download_button("📥 KPIをHTMLでダウンロード", html_content_kpi, "kpi_comparison.html", "text/html", key="kpi_dl")
            
            # ========== タブ2: 収益・コスト構造 ==========
            with tab_structure:
                st.subheader("収益・コスト構造の比較")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("##### 📊 収益構造")
                    fig1, ax1 = plt.subplots(figsize=(10, 6))
                    
                    companies = df_compare['企業名_表示'].tolist()  # 表示名
                    sales = df_compare['売上高'].tolist()
                    revenue = df_compare['営業収入'].tolist()
                    
                    ax1.bar(companies, sales, label='売上高', color='#2E86AB')
                    ax1.bar(companies, revenue, bottom=sales, label='営業収入', color='#A23B72')
                    ax1.set_ylabel('金額（百万円）')
                    ax1.set_title('収益構造（売上高＋営業収入）')
                    ax1.legend()
                    ax1.tick_params(axis='x', rotation=45)
                    plt.tight_layout()
                    st.pyplot(fig1)
                
                with col2:
                    st.markdown("##### 📊 コスト構造（対売上高比率）")
                    fig2, ax2 = plt.subplots(figsize=(10, 6))
                    
                    cost_ratio = 100 - df_compare['売上総利益率']
                    sgna_ratio = safe_divide(df_compare['販管費'] * 100, df_compare['売上高'])
                    profit_ratio = df_compare['営業利益率']
                    
                    ax2.bar(companies, cost_ratio.tolist(), label='売上原価率', color='#C73E1D')
                    ax2.bar(companies, sgna_ratio.tolist(), bottom=cost_ratio.tolist(), label='販管費率', color='#F18F01')
                    ax2.bar(companies, profit_ratio.tolist(), bottom=(cost_ratio + sgna_ratio).tolist(), label='営業利益率', color='#95C623')
                    
                    # 数値ラベル
                    for i, (c, s, p) in enumerate(zip(cost_ratio, sgna_ratio, profit_ratio)):
                        ax2.text(i, c/2, f'{c:.1f}', ha='center', va='center', color='white', fontsize=8)
                        ax2.text(i, c + s/2, f'{s:.1f}', ha='center', va='center', color='white', fontsize=8)
                        ax2.text(i, c + s + p/2, f'{p:.1f}', ha='center', va='center', color='white', fontsize=8)
                    
                    ax2.set_ylabel('比率（%）')
                    ax2.set_title('コスト構造分解')
                    ax2.legend(loc='upper right')
                    ax2.tick_params(axis='x', rotation=45)
                    plt.tight_layout()
                    st.pyplot(fig2)
                
                # 構造比較テーブル
                st.markdown("##### 📋 構造比較テーブル")
                structure_df = df_compare[['企業名_表示']].copy()
                structure_df['売上原価率'] = (100 - df_compare['売上総利益率']).round(1)
                structure_df['販管費率'] = safe_divide(df_compare['販管費'] * 100, df_compare['売上高']).round(1)
                structure_df['営業利益率'] = df_compare['営業利益率'].round(1)
                structure_df = structure_df.rename(columns={'企業名_表示': '企業名'}).set_index('企業名')
                
                st.dataframe(
                    structure_df.style.format('{:.1f}%').background_gradient(cmap='RdYlGn', subset=['営業利益率']),
                    use_container_width=True
                )
                
                # 統合チャートを作成してHTMLダウンロード用に保存
                fig_structure, axs_structure = plt.subplots(1, 2, figsize=(14, 5))
                
                companies = df_compare['企業名_表示'].tolist()  # 表示名
                sales = df_compare['売上高'].tolist()
                revenue = df_compare['営業収入'].tolist()
                
                axs_structure[0].bar(companies, sales, label='売上高', color='#2E86AB')
                axs_structure[0].bar(companies, revenue, bottom=sales, label='営業収入', color='#A23B72')
                axs_structure[0].set_ylabel('金額（百万円）')
                axs_structure[0].set_title('収益構造（売上高＋営業収入）')
                axs_structure[0].legend()
                axs_structure[0].tick_params(axis='x', rotation=45)
                
                cost_ratio = 100 - df_compare['売上総利益率']
                sgna_ratio = safe_divide(df_compare['販管費'] * 100, df_compare['売上高'])
                profit_ratio = df_compare['営業利益率']
                
                axs_structure[1].bar(companies, cost_ratio.tolist(), label='売上原価率', color='#C73E1D')
                axs_structure[1].bar(companies, sgna_ratio.tolist(), bottom=cost_ratio.tolist(), label='販管費率', color='#F18F01')
                axs_structure[1].bar(companies, profit_ratio.tolist(), bottom=(cost_ratio + sgna_ratio).tolist(), label='営業利益率', color='#95C623')
                axs_structure[1].set_ylabel('比率（%）')
                axs_structure[1].set_title('コスト構造分解')
                axs_structure[1].legend(loc='upper right')
                axs_structure[1].tick_params(axis='x', rotation=45)
                
                plt.tight_layout()
                plt.close(fig_structure)
                
                html_content = get_html_report(structure_df, f"収益・コスト構造比較 - {format_fy(selected_year)}", fig_structure)
                st.download_button("📥 HTMLでダウンロード（チャート＋テーブル）", html_content, "structure_comparison.html", "text/html", key="structure_dl")
            
            # ========== タブ3: 財政状態(BS) ==========
            with tab_bs:
                st.subheader("財政状態の比較")
                
                # 追加指標の計算
                df_bs = df_compare.copy()
                df_bs['棚卸資産回転率'] = safe_divide(df_bs['売上高'], df_bs['棚卸資産']).round(1)
                
                fig, axs = plt.subplots(2, 2, figsize=(14, 10))
                companies_data = df_bs['企業名'].tolist()
                companies = df_bs['企業名_表示'].tolist()  # 表示名
                colors = [company_colors[c] for c in companies_data]
                
                # 総資産
                axs[0, 0].bar(companies, df_bs['総資産'], color=colors)
                axs[0, 0].set_title('総資産（百万円）', fontsize=12, fontweight='bold')
                axs[0, 0].tick_params(axis='x', rotation=45)
                
                # 棚卸資産
                axs[0, 1].bar(companies, df_bs['棚卸資産'], color='#95C623')
                axs[0, 1].set_title('棚卸資産（百万円）', fontsize=12, fontweight='bold')
                axs[0, 1].tick_params(axis='x', rotation=45)
                
                # 総資産回転率
                axs[1, 0].plot(companies, df_bs['総資産回転率'].tolist(), marker='o', markersize=10, linewidth=2, color='#5C4D7D')
                axs[1, 0].set_title('総資産回転率（回）', fontsize=12, fontweight='bold')
                axs[1, 0].tick_params(axis='x', rotation=45)
                for i, v in enumerate(df_bs['総資産回転率']):
                    axs[1, 0].text(i, v + 0.05, f'{v:.2f}', ha='center', fontsize=9)
                
                # 棚卸資産回転率
                axs[1, 1].plot(companies, df_bs['棚卸資産回転率'].tolist(), marker='s', markersize=10, linewidth=2, color='#C73E1D')
                axs[1, 1].set_title('棚卸資産回転率（回）', fontsize=12, fontweight='bold')
                axs[1, 1].tick_params(axis='x', rotation=45)
                for i, v in enumerate(df_bs['棚卸資産回転率']):
                    axs[1, 1].text(i, v + 0.3, f'{v:.1f}', ha='center', fontsize=9)
                
                plt.tight_layout()
                st.pyplot(fig)
                
                # チャートを保存（HTMLダウンロード用）
                fig_bs = fig
                
                # データテーブル
                st.markdown("##### 📋 詳細データ")
                bs_cols = ['企業名_表示', '総資産', '流動資産', '固定資産', '棚卸資産', '有利子負債', '純資産', '自己資本比率', '総資産回転率', '棚卸資産回転率']
                bs_display = df_bs[[c for c in bs_cols if c in df_bs.columns]].copy()
                bs_display = bs_display.rename(columns={'企業名_表示': '企業名'}).set_index('企業名')
                st.dataframe(
                    bs_display.style.format({
                        '総資産': '{:,.0f}', '流動資産': '{:,.0f}', '固定資産': '{:,.0f}',
                        '棚卸資産': '{:,.0f}', '有利子負債': '{:,.0f}', '純資産': '{:,.0f}',
                        '自己資本比率': '{:.1f}', '総資産回転率': '{:.2f}', '棚卸資産回転率': '{:.1f}'
                    }),
                    use_container_width=True
                )
                
                html_content = get_html_report(bs_display, f"財政状態比較 - {format_fy(selected_year)}", fig_bs)
                st.download_button("📥 HTMLでダウンロード（チャート＋テーブル）", html_content, "bs_comparison.html", "text/html", key="bs_dl")
            
            # ========== タブ4: キャッシュフロー ==========
            with tab_cf:
                st.subheader("キャッシュフローの比較")
                
                fig, axs = plt.subplots(2, 2, figsize=(14, 10))
                companies = df_compare['企業名_表示'].tolist()  # 表示名
                
                # 営業CF
                cf_colors = ['#2E86AB' if v >= 0 else '#C73E1D' for v in df_compare['営業CF']]
                axs[0, 0].bar(companies, df_compare['営業CF'], color=cf_colors)
                axs[0, 0].axhline(y=0, color='black', linewidth=0.5)
                axs[0, 0].set_title('営業キャッシュフロー（百万円）', fontsize=12, fontweight='bold')
                axs[0, 0].tick_params(axis='x', rotation=45)
                
                # 投資CF
                inv_colors = ['#2E86AB' if v >= 0 else '#F18F01' for v in df_compare['投資CF']]
                axs[0, 1].bar(companies, df_compare['投資CF'], color=inv_colors)
                axs[0, 1].axhline(y=0, color='black', linewidth=0.5)
                axs[0, 1].set_title('投資キャッシュフロー（百万円）', fontsize=12, fontweight='bold')
                axs[0, 1].tick_params(axis='x', rotation=45)
                
                # 財務CF
                fin_colors = ['#95C623' if v >= 0 else '#A23B72' for v in df_compare['財務CF']]
                axs[1, 0].bar(companies, df_compare['財務CF'], color=fin_colors)
                axs[1, 0].axhline(y=0, color='black', linewidth=0.5)
                axs[1, 0].set_title('財務キャッシュフロー（百万円）', fontsize=12, fontweight='bold')
                axs[1, 0].tick_params(axis='x', rotation=45)
                
                # フリーCF
                free_colors = ['#95C623' if v >= 0 else '#C73E1D' for v in df_compare['フリーCF']]
                axs[1, 1].bar(companies, df_compare['フリーCF'], color=free_colors)
                axs[1, 1].axhline(y=0, color='black', linewidth=0.5)
                axs[1, 1].set_title('フリーキャッシュフロー（百万円）', fontsize=12, fontweight='bold')
                axs[1, 1].tick_params(axis='x', rotation=45)
                
                plt.tight_layout()
                st.pyplot(fig)
                
                # CF比較棒グラフ
                st.markdown("##### 📊 キャッシュフロー構成比較")
                fig2, ax2 = plt.subplots(figsize=(12, 5))
                x = np.arange(len(companies))
                width = 0.2
                
                ax2.bar(x - width*1.5, df_compare['営業CF'], width, label='営業CF', color='#2E86AB')
                ax2.bar(x - width*0.5, df_compare['投資CF'], width, label='投資CF', color='#F18F01')
                ax2.bar(x + width*0.5, df_compare['財務CF'], width, label='財務CF', color='#A23B72')
                ax2.bar(x + width*1.5, df_compare['フリーCF'], width, label='フリーCF', color='#95C623')
                
                ax2.axhline(y=0, color='black', linewidth=0.5)
                ax2.set_xticks(x)
                ax2.set_xticklabels(companies, rotation=45, ha='right')
                ax2.legend()
                ax2.set_ylabel('金額（百万円）')
                plt.tight_layout()
                st.pyplot(fig2)
                
                # データテーブル
                cf_cols = ['企業名_表示', '営業CF', '投資CF', '財務CF', 'フリーCF', '現金及び預金']
                cf_display = df_compare[[c for c in cf_cols if c in df_compare.columns]].copy()
                cf_display = cf_display.rename(columns={'企業名_表示': '企業名'}).set_index('企業名')
                st.dataframe(
                    cf_display.style.format('{:,.0f}'),
                    use_container_width=True
                )
                
                html_content = get_html_report(cf_display, f"キャッシュフロー比較 - {format_fy(selected_year)}", fig2)
                st.download_button("📥 HTMLでダウンロード（チャート＋テーブル）", html_content, "cf_comparison.html", "text/html", key="cf_dl")
            
            # ========== タブ5: 労働生産性 ==========
            with tab_prod:
                st.subheader("労働生産性の比較")
                
                # 生産性指標の計算
                df_prod = df_compare.copy()
                total_employees = df_prod['従業員数'] + df_prod['パート社員'].fillna(0)
                
                df_prod['正社員1人当り売上高'] = safe_divide(df_prod['売上高'], df_prod['従業員数']).round(2)
                df_prod['正社員1人当り営業利益'] = safe_divide(df_prod['営業利益'], df_prod['従業員数']).round(2)
                df_prod['全従業員1人当り売上高'] = safe_divide(df_prod['売上高'], total_employees).round(2)
                df_prod['全従業員1人当り営業利益'] = safe_divide(df_prod['営業利益'], total_employees).round(2)
                
                fig, axs = plt.subplots(2, 2, figsize=(14, 10))
                companies_data = df_prod['企業名'].tolist()
                companies = df_prod['企業名_表示'].tolist()  # 表示名
                colors = [company_colors[c] for c in companies_data]
                
                # 正社員1人当り売上高
                axs[0, 0].bar(companies, df_prod['正社員1人当り売上高'], color=colors)
                axs[0, 0].set_title('正社員1人当り売上高（百万円）', fontsize=12, fontweight='bold')
                axs[0, 0].tick_params(axis='x', rotation=45)
                
                # 正社員1人当り営業利益
                axs[0, 1].bar(companies, df_prod['正社員1人当り営業利益'], color='#F18F01')
                axs[0, 1].set_title('正社員1人当り営業利益（百万円）', fontsize=12, fontweight='bold')
                axs[0, 1].tick_params(axis='x', rotation=45)
                
                # 全従業員1人当り売上高
                axs[1, 0].bar(companies, df_prod['全従業員1人当り売上高'], color='#95C623')
                axs[1, 0].set_title('全従業員1人当り売上高（百万円）', fontsize=12, fontweight='bold')
                axs[1, 0].tick_params(axis='x', rotation=45)
                
                # 全従業員1人当り営業利益
                axs[1, 1].bar(companies, df_prod['全従業員1人当り営業利益'], color='#C73E1D')
                axs[1, 1].set_title('全従業員1人当り営業利益（百万円）', fontsize=12, fontweight='bold')
                axs[1, 1].tick_params(axis='x', rotation=45)
                
                plt.tight_layout()
                st.pyplot(fig)
                
                # チャートを保存（HTMLダウンロード用）
                fig_prod = fig
                
                # データテーブル
                prod_cols = ['企業名_表示', '従業員数', 'パート社員', '正社員1人当り売上高', '正社員1人当り営業利益', 
                            '全従業員1人当り売上高', '全従業員1人当り営業利益']
                prod_display = df_prod[[c for c in prod_cols if c in df_prod.columns]].copy()
                prod_display = prod_display.rename(columns={'企業名_表示': '企業名'}).set_index('企業名')
                st.dataframe(
                    prod_display.style.format({
                        '従業員数': '{:,.0f}', 'パート社員': '{:,.0f}',
                        '正社員1人当り売上高': '{:.2f}', '正社員1人当り営業利益': '{:.2f}',
                        '全従業員1人当り売上高': '{:.2f}', '全従業員1人当り営業利益': '{:.2f}'
                    }),
                    use_container_width=True
                )
                
                html_content = get_html_report(prod_display, f"労働生産性比較 - {format_fy(selected_year)}", fig_prod)
                st.download_button("📥 HTMLでダウンロード（チャート＋テーブル）", html_content, "productivity_comparison.html", "text/html", key="prod_dl")
            
            # --- トレンド表示（オプション） ---
            if show_trend and not df_trend.empty:
                st.divider()
                st.subheader(f"📈 過去5年トレンド分析（{format_fy(selected_year-4)}〜{format_fy(selected_year)}）")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_trend1, ax_trend1 = plt.subplots(figsize=(10, 5))
                    for company in selected_companies:
                        company_trend = df_trend[df_trend['企業名'] == company].sort_values('決算年度')
                        if not company_trend.empty:
                            display_name = get_display_name(company)
                            ax_trend1.plot(
                                company_trend['決算年度'].apply(format_fy), 
                                company_trend['売上高'], 
                                marker='o', label=display_name, color=company_colors[company]
                            )
                    ax_trend1.set_title('売上高推移')
                    ax_trend1.legend(loc='upper left', fontsize=8)
                    ax_trend1.tick_params(axis='x', rotation=45)
                    plt.tight_layout()
                    st.pyplot(fig_trend1)
                
                with col2:
                    fig_trend2, ax_trend2 = plt.subplots(figsize=(10, 5))
                    for company in selected_companies:
                        company_trend = df_trend[df_trend['企業名'] == company].sort_values('決算年度')
                        if not company_trend.empty:
                            display_name = get_display_name(company)
                            ax_trend2.plot(
                                company_trend['決算年度'].apply(format_fy), 
                                company_trend['営業利益率'], 
                                marker='s', label=display_name, color=company_colors[company]
                            )
                    ax_trend2.set_title('営業利益率推移（%）')
                    ax_trend2.legend(loc='upper left', fontsize=8)
                    ax_trend2.tick_params(axis='x', rotation=45)
                    plt.tight_layout()
                    st.pyplot(fig_trend2)

else:
    st.error("""
    ⚠️ データファイルが見つかりません。
    
    以下の手順でデータを配置してください：
    1. `data/` フォルダを作成
    2. `financial_data.xlsx` を配置
    
    必要な列: 企業名, 決算年度, 売上高, 営業利益, 営業利益率 など
    """)

# --- フッター ---
st.divider()
st.markdown("""
<div style="text-align: center; color: #888; font-size: 12px;">
    📊 企業財務比較ダッシュボード | Powered by Streamlit
</div>
""", unsafe_allow_html=True)
