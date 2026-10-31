# Codyssey-B2-1: 나만의 용돈 기입장 프로그램 만들기
Python 표준 라이브러리만을 활용하여 구축된 파일 입출력 기반의 콘솔 가계부 서비스입니다.  
제너레이터 스트리밍을 통한 대용량 데이터 처리, 데코레이터를 이용한 관심사 분리, 엄격한 타입 힌트, 계층별 모듈화(CLI / Service / Repository / Model)를 통해 데이터 안정성과 유지보수성을 극대화하도록 설계되었습니다.

---

## 목차
1. [개발 및 실행 환경](#개발-및-실행-환경)
2. [저장 파일 위치 및 형식](#저장-파일-위치-및-형식)
3. [명령어 사용법 및 예시](#명령어-사용법-및-예시)
4. [CSV Import / Export 스키마](#csv-import--export-스키마)
5. [아키텍처 및 설계 특징](#아키텍처-및-설계-특징)
6. [테스트 실행 방법](#테스트-실행-방법)

---

## 개발 및 실행 환경

- **언어**: Python 3.10 이상 권장 (Python 3.9+ 호환)
- **외부 라이브러리 의존성**: 없음 (Python 표준 라이브러리만 사용)
- **기본 실행 명령**:
  ```bash
  python -m budget_app <command> [options]
  ```
  *(모든 명령어에 `--help` 옵션을 지정하여 세부 사용 방법을 확인할 수 있습니다.)*

---

## 저장 파일 위치 및 형식

데이터는 3개의 JSONL(JSON Lines) 파일로 영구 분리 저장됩니다.  
기본 저장 경로는 `./data` 이며, 실행 시 `--data-dir <path>` 옵션으로 변경할 수 있습니다. 저장 폴더나 파일이 없을 경우 초기 실행 시 자동 생성됩니다.

1. **`./data/transactions.jsonl`**: 거래 내역 파일 (줄단위 JSON)
   ```json
   {"id": "TX-000001", "date": "2024-01-15", "type": "expense", "amount": 15000, "category": "food", "memo": "점심", "tags": ["meal"]}
   ```
2. **`./data/categories.jsonl`**: 카테고리 목록 파일
   - 초기 실행 시 기본 카테고리(`food`, `transport`, `living`, `leisure`, `salary`, `etc`)가 자동 등록됩니다.
   ```json
   {"name": "food"}
   {"name": "transport"}
   ```
3. **`./data/budgets.jsonl`**: 월별 예산 파일
   ```json
   {"month": "2024-01", "amount": 500000}
   ```

---

## 명령어 사용법 및 예시

### 1. 거래 추가 (`add`)
대화형(`input()`) 프롬프트로 날짜, 타입, 카테고리, 금액, 메모, 태그를 입력받습니다. 잘못된 형식 입력 시 오류 및 힌트를 출력하고 재입력을 요청합니다.
```bash
$ python -m budget_app add
날짜(YYYY-MM-DD): 2024-01-15
타입(income/expense): expense
카테고리: food
금액(양수): 15000
메모(선택): 점심
태그(쉼표로 구분, 없으면 엔터): meal
[저장 완료] id=TX-000001
```

### 2. 거래 목록 (`list`)
최신 거래부터 역순으로 스트리밍 조회합니다.
- `--limit N`: 조회할 건수 (기본값: 20)
```bash
$ python -m budget_app list --limit 3
TX-000003 | 2024-01-15 | expense | food | 15000 | 점심 | [meal]
TX-000002 | 2024-01-14 | income | salary | 3000000 | 급여
TX-000001 | 2024-01-12 | expense | transport | 20000 | 교통비
```

### 3. 거래 검색 (`search`)
여러 조건을 조합하여 최신순으로 검색할 수 있습니다.
- 옵션: `--from`, `--to`, `--category`, `--type`, `--q`, `--tag`
```bash
$ python -m budget_app search --from 2024-01-01 --to 2024-01-31 --type expense --category food
TX-000003 | 2024-01-15 | expense | food | 15000 | 점심 | [meal]
```

### 4. 월별 요약 및 예산 점검 (`summary`)
해당 월의 총 수입, 총 지출, 잔액 및 지출 상위 TOP N 카테고리를 출력합니다. 예산이 등록되어 있다면 예산 사용률과 초과 경고를 표시합니다.
- `--month YYYY-MM` (필수)
- `--top N`: 지출 상위 카테고리 수 (기본값: 3)
```bash
$ python -m budget_app summary --month 2024-01 --top 3
총 수입: 3000000원
총 지출: 215000원
잔액: 2785000원
예산: 500000원 (사용률 43.0%)

지출 TOP 3:
1) living 150000원
2) food 45000원
3) transport 20000원
```

### 5. 예산 관리 (`budget`)
월별 예산을 등록하거나 조회합니다.
- 예산 설정: `budget set --month YYYY-MM --amount <금액>`
- 예산 목록 조회: `budget list`
```bash
$ python -m budget_app budget set --month 2024-01 --amount 500000
[저장 완료] 2024-01 예산 500000원

$ python -m budget_app budget list
- 2024-01: 500000원
```

### 6. 카테고리 관리 (`category`)
카테고리 목록 조회, 추가, 삭제를 제공합니다. 사용 중인 카테고리는 데이터 무결성을 위해 삭제할 수 없도록 방지합니다.
- 카테고리 목록: `category list`
- 카테고리 추가: `category add [이름]` (이름 생략 시 대화형 입력)
- 카테고리 삭제: `category remove [이름]` (이름 생략 시 대화형 입력)
```bash
$ python -m budget_app category list
- food
- transport
- living

$ python -m budget_app category add health
[저장 완료] category=health

$ python -m budget_app category remove health
[삭제 완료] category=health
```

### 7. 거래 수정 (`update`)
거래 ID를 기준으로 필드를 수정합니다 (옵션 인자 기반 방식 채택).
- `update --id <id> [--date ...] [--type ...] [--category ...] [--amount ...] [--memo ...] [--tags ...]`
```bash
$ python -m budget_app update --id TX-000001 --amount 20000 --memo "저녁 식사"
[수정 완료] id=TX-000001
```

### 8. 거래 삭제 (`delete`)
거래 ID를 지정하여 내역을 삭제합니다.
```bash
$ python -m budget_app delete --id TX-000001
[삭제 완료] id=TX-000001
```

### 9. CSV 내보내기 (`export`)
조건에 맞는 거래 내역을 표준 CSV 파일로 내보냅니다.
- `--out <경로>` (필수)
- `--month YYYY-MM` 또는 `--from YYYY-MM-DD --to YYYY-MM-DD` 중 최소 1개 필수
```bash
$ python -m budget_app export --out export.csv --month 2024-01
[완료] export.csv (12 records)
```

### 10. CSV 가져오기 (`import`)
CSV 파일로부터 거래 내역을 일괄 등록합니다.
- `--from <파일경로>` (필수)
```bash
$ python -m budget_app import --from import.csv
[완료] imported=5, skipped=0
```

---

## CSV Import / Export 스키마

CSV 파일은 **UTF-8 인코딩**과 **헤더 행**을 포함해야 합니다.

| 컬럼명 | 필수 여부 | 형식 | 설명 및 예시 |
|:---|:---:|:---|:---|
| `date` | Y | `YYYY-MM-DD` | 거래 날짜 (예: `2024-01-15`) |
| `type` | Y | `income` / `expense` | 거래 유형 |
| `category` | Y | 문자열 | 등록된 카테고리명 (예: `food`) |
| `amount` | Y | 양수 정수 | 0보다 큰 금액 (예: `15000`) |
| `memo` | N | 문자열 | 메모 (예: `점심 식사`) |
| `tags` | N | 쉼표 구분 문자열 | 태그 목록 (예: `lunch,meal`) |

예시:
```csv
date,type,category,amount,memo,tags
2024-01-10,income,salary,3000000,1월 급여,main
2024-01-15,expense,food,15000,점심,meal,lunch
```

---

## 아키텍처 및 설계 특징

- **계층형 아키텍처 (Layered Architecture)**:
  - `CLI (cli.py)`: 명령행 인자 파싱 및 대화형 입출력 UX 담당
  - `Service (service.py)`: 비즈니스 규칙, 무결성 제약, 통계 집계 등 로직 담당
  - `Repository (repository.py)`: JSONL 파일 스트리밍 I/O 및 데이터 영구화 담당
  - `Models (models.py)`: `dataclass` 기반 데이터 모델 정의
  - `Validator (validator.py)`: 입력값 정규화 및 유효성 검증
  - `Exceptions (exceptions.py)`: 원인과 힌트를 담는 도메인 예외 체계
  - `Decorators (decorators.py)`: 오류 처리(`@handle_cli_errors`), 실행 시간 측정(`@timed_execution`) 등 관심사 분리
- **제너레이터 기반 메모리 스트리밍 (`yield`)**:
  - `list` 및 `search` 시 파일 전체를 메모리에 적재하지 않고, 파일 끝에서부터 버퍼 단위로 역방향 탐색하는 스트리밍 제너레이터(`reverse_readline_generator`)를 구현하여 메모리 사용량을 $O(1)$로 유지합니다.
- **파일 저장 안전성 (원자적 교체)**:
  - 수정(`update`) 및 삭제(`delete`) 시 임시 파일(`tempfile`)에 작성 후 `os.replace`를 수행하여 쓰기 도중 프로그램이 중단되어도 파일이 손상되지 않도록 보호합니다.
- **사용자 친화적 예외 처리**:
  - 사용자에게 스택트레이스를 노출하지 않고 `[오류]`와 `[힌트]`로 명확한 해결 가이드를 제공하며, 종료 코드(비정상: 1, 취소: 130, 정상: 0)를 준수합니다.

---

## 테스트 실행 방법

Python 내장 `unittest` 프레임워크를 통해 외부 라이브러리 없이 전체 테스트를 수행할 수 있습니다.

```bash
python -m unittest discover -s tests
```
