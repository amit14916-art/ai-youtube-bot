import { Composition, getInputProps } from "remotion";
import { MainVideo } from "./MainVideo";

export const RemotionVideo: React.FC = () => {
    const inputProps = getInputProps() as any;

    // Calculate actual total duration from dynamic JSON props
    let totalDuration = 300;
    if (inputProps && inputProps.slides && inputProps.slides.length > 0) {
        totalDuration = inputProps.slides.reduce((acc: number, slide: any) => acc + slide.durationInFrames, 0);
    }

    return (
        <>
            <Composition
                id="MainVideo"
                component={MainVideo}
                durationInFrames={totalDuration}
                fps={30}
                width={1080}
                height={1920}
                defaultProps={{
                    slides: [],
                    audioUrl: "",
                    bgmUrl: "",
                    wordTimings: [],
                    isShorts: true,
                    ...inputProps
                }}
            />
        </>
    );
};
