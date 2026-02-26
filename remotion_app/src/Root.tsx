import { Composition } from "remotion";
import { MainVideo } from "./MainVideo";

// We keep a default schema but pass dynamic props via JSON file when rendering
export const RemotionVideo: React.FC = () => {
    return (
        <>
            <Composition
                id="MainVideo"
                component={MainVideo}
                durationInFrames={300} // This will be dynamically overridden by --props 
                fps={30}
                width={1080}
                height={1920}
                defaultProps={{
                    slides: [],
                    audioUrl: "",
                    bgmUrl: "",
                    wordTimings: [],
                    isShorts: true
                }}
            />
        </>
    );
};
