# 고스티 동글유령체

둥글고 귀여운 손글씨 TTF입니다. 영문 이름은 **Ghosty Round Ghost**, 스타일은 **Regular**입니다. 배포 버전은 **v1.7**, TTF 내부 버전은 **1.700**입니다.

## 사용 방법

`GhostyRoundGhost-Regular.ttf`를 운영체제에 설치한 뒤 사용하는 프로그램에서 **고스티 동글유령체** 또는 **Ghosty Round Ghost**를 선택합니다. 프로그램에 글꼴 파일을 직접 지정해 사용할 수도 있습니다.

## 지원 범위

- 한글 완성형 11,172자 전체와 현대 조합 자모 67자
- 호환 자모, 영문 대·소문자, 숫자, 문장 부호와 기호
- 총 11,490개 유니코드 문자
- 완성형과 자모 분리 입력 지원

`♤`, `♧`, `†`, `‡`, `£`, `¢`에는 여섯 종류의 유령 장식이 들어 있습니다. 이 글꼴에서 `£`와 `¢`는 통화 기호 대신 유령으로 표시됩니다.

## 미리보기

미리보기 이미지는 아래 **5개만 유지**합니다.

| 파일 | 내용 |
|---|---|
| [native-640x480.png](preview/native-640x480.png) | 기본 크기 예제 |
| [specimen-2x.png](preview/specimen-2x.png) | 두 배 해상도로 직접 렌더링한 예제 |
| [all-hangul-native-24px.png](preview/all-hangul-native-24px.png) | 한글 완성형 전체 |
| [hangul-contexts-native-32px.png](preview/hangul-contexts-native-32px.png) | 자모 조합과 받침 예제 |
| [jamo-symbols-native-32px.png](preview/jamo-symbols-native-32px.png) | 자모·영문·숫자·기호 |

## 라이선스

**The Unlicense**로 공개합니다. 출처 표시, 수정 사항 공개, 허가 요청 없이 사용·임베딩·수정·이름 변경·재배포·유료 판매할 수 있습니다. 글꼴 자체의 판매도 가능합니다. 법이 허용하는 최대 범위에서 저작권을 포기하며, 자세한 내용은 [LICENSE](LICENSE)를 확인하세요.

글꼴과 원본 제작·미리보기 스크립트에 적용합니다. 외부 Python 라이브러리와 참조 글꼴은 각자의 라이선스를 따릅니다.

## 제작 및 검증

Python 3.10 이상에서 실행합니다.

```text
python -m pip install -r requirements.txt
python tools/build_ghosty_font.py
python -m unittest discover -s tests -v
python tools/preview_ghosty_font.py
python tools/package_release.py --version 1.7
```

`tools/`에는 원본 중심선, 제작·검증·미리보기 도구가 있고 `tests/`에는 Python 회귀 검사가 있습니다. 문자 범위, 점 크기, 잘림, 한글 NFC/NFD 일치, 자모 겹침, 겹받침 공간, 모음 세로획과 여러 크기의 렌더링을 검사합니다.

## 배포 ZIP

`dist/GhostyRoundGhost-v1.7.zip`에는 TTF, LICENSE, README와 위의 미리보기 5개가 포함됩니다. 제작 도구와 테스트 코드는 저장소에서 제공합니다.
