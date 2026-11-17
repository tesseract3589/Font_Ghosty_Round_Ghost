# 고스티 동글유령체

둥글고 귀여운 느낌을 주는 손글씨 TTF. 영문 내부 이름은 **Ghosty Round Ghost**, 스타일은 **Regular** 한 종류이며 현재 버전은 **1.700**이다.

## 1.700 수정

점은 선 굵기와 같은 지름을 쓰는 대신, 시각적으로 충분히 도톰하게 보이도록 지름을 100에서 150 font unit으로 늘렸다. 마침표·가운뎃점·말줄임표·콜론·느낌표·물음표와 i/j, 합자의 점까지 적용했다. 일반 선 굵기 100 unit은 유지한다.

받침이 있는 ㅗ·ㅛ·ㅜ·ㅠ 조합의 모음 칸 높이를 100에서 200 unit으로 늘렸다. 세로획 중심선 길이가 약 60에서 120 unit으로 늘어나도록 하고, 초성과 종성 배치를 함께 조정해 접촉을 방지했다. 곡·국·눈·붑·옹·숭·숯 등으로 작은 크기의 가독성을 검사한다.

`preview/stems-and-dots-before-after.png`에서 이전 버전과 비교할 수 있다.

## 라이선스

이 글꼴과 원본 제작·미리보기 스크립트는 **The Unlicense**로 공개한다. 출처 표시, 수정 사항 공개, 허가 요청 없이 사용·임베딩·수정·이름 변경·재배포·유료 판매할 수 있다. 글꼴 자체의 판매도 가능하다. 법이 허용하는 최대 범위에서 저작권을 포기한다. TTF 내부 라이선스 정보도 저장소의 Unlicense와 일치한다. 자세한 범위는 [LICENSE](LICENSE)에 있다.

- 파일: `GhostyRoundGhost-Regular.ttf`
- 한글 완성형 11,172자 전체, 현대 조합 자모 67자, 호환 자모, 영문 대·소문자, 숫자와 기호를 포함한 **11,490개 유니코드 문자**를 지원한다.
## 독립 제작 환경

Godot와 게임 프로젝트 없이 Python 3.10 이상에서 제작·검증·미리보기를 실행한다.

```text
python -m pip install -r requirements.txt
python tools/build_ghosty_font.py
python -m unittest discover -s tests -v
python tools/preview_ghosty_font.py
```

- `GhostyRoundGhost-Regular.ttf`: 완성된 글꼴
- `LICENSE`: The Unlicense
- `tools/`: 원본 중심선, 빌드·검증·미리보기 도구와 문자 범위 및 검증 보고서
- `tests/test_font.py`: Python 기반 회귀 검사
- `preview/`: 직접 렌더링한 미리보기와 전체 문자 시트

빌드는 모든 한글 조합의 자모 겹침과 속공간, 같은 획 굵기와 겹받침 간격을 검사한다. 테스트는 문자 범위, 점 크기, 잘림, NFC/NFD 조합 일치, 라이선스 정보, 재빌드 시 글리프·메트릭 일치, 작은 크기의 래스터와 두 해상도의 독립 렌더링을 검사한다. 결과는 `tools/readability.json`, `tools/validation.json`에 기록한다.

Godot 전용 `font_smoke.gd`는 가져오지 않았다. 이 저장소의 테스트와 미리보기에는 Godot가 필요 없다. 기존 미리보기 파일도 Python 도구로 다시 생성할 수 있다. 선택적으로 `--before <이전 TTF 경로>`를 미리보기 명령에 추가하면 수정 전후 비교도 생성한다.

게임에는 루트 TTF와 LICENSE의 복사본만 배포 자산으로 넣는다. 게임의 임포트 설정은 게임 쪽에서 관리한다. 원본 참조 폰트와 외부 Python 라이브러리는 이 저장소의 라이선스 적용 범위에 포함하지 않는다.
